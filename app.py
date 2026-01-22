import streamlit as st
import requests
from datetime import datetime
import socket
import ssl
import re
import random
import time
from PIL import Image
import io
import base64
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import pandas as pd
from io import StringIO
from bs4 import BeautifulSoup
import hashlib
import subprocess
import platform
import json

# ============================================================================
# PART 1: IMPORT GUARDS AND CONFIGURATION
# ============================================================================

# Optional imports with availability flags
DNS_AVAILABLE = False
WHOIS_AVAILABLE = False
MYSQL_AVAILABLE = False
IMAPLIB_AVAILABLE = False
SMTPLIB_AVAILABLE = False
FTPLIB_AVAILABLE = False
PYTZ_AVAILABLE = False

try:
    import dns.resolver
    import dns.query
    import dns.zone
    DNS_AVAILABLE = True
except ImportError:
    pass

try:
    import whois
    WHOIS_AVAILABLE = True
except ImportError:
    pass

try:
    import pymysql
    MYSQL_AVAILABLE = True
except ImportError:
    pass

try:
    import imaplib
    import smtplib
    import email
    from email import policy
    from email.parser import BytesParser
    IMAPLIB_AVAILABLE = True
    SMTPLIB_AVAILABLE = True
except ImportError:
    pass

try:
    import ftplib
    FTPLIB_AVAILABLE = True
except ImportError:
    pass

try:
    import pytz
    PYTZ_AVAILABLE = True
except ImportError:
    pass

# Feature availability dictionary
FEATURES = {
    'dns': DNS_AVAILABLE,
    'whois': WHOIS_AVAILABLE,
    'mysql': MYSQL_AVAILABLE,
    'email': IMAPLIB_AVAILABLE and SMTPLIB_AVAILABLE,
    'ftp': FTPLIB_AVAILABLE,
    'timezone': PYTZ_AVAILABLE
}

# Configuration
CONFIG = {
    'request_timeout': 10,
    'dns_timeout': 5,
    'max_redirects': 10,
    'user_agent': 'SupportBuddy/1.0',
    'cache_ttl': 300  # 5 minutes
}

# Configure Gemini API
GEMINI_API_KEY = ""
GEMINI_AVAILABLE = False
try:
    GEMINI_API_KEY = st.secrets.get("GEMINI_API_KEY", "")
    if GEMINI_API_KEY:
        import google.generativeai as genai
        genai.configure(api_key=GEMINI_API_KEY)
        GEMINI_AVAILABLE = True
except:
    pass

# Page Configuration
st.set_page_config(
    page_title="Support Buddy - Complete Toolkit",
    page_icon="🔧",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Enhanced Custom CSS
st.markdown("""
    <style>
    .main { padding: 1rem 2rem; }
    .success-box {
        padding: 1.5rem; border-radius: 12px;
        background: linear-gradient(135deg, #d1fae5 0%, #a7f3d0 100%);
        border-left: 6px solid #10b981; margin: 1rem 0;
    }
    .warning-box {
        padding: 1.5rem; border-radius: 12px;
        background: linear-gradient(135deg, #fef3c7 0%, #fde68a 100%);
        border-left: 6px solid #f59e0b; margin: 1rem 0;
    }
    .error-box {
        padding: 1.5rem; border-radius: 12px;
        background: linear-gradient(135deg, #fee2e2 0%, #fecaca 100%);
        border-left: 6px solid #ef4444; margin: 1rem 0;
    }
    .info-box {
        padding: 1.5rem; border-radius: 12px;
        border-left: 6px solid #3b82f6; margin: 1rem 0;
    }
    </style>
""", unsafe_allow_html=True)

# Session state initialization
if 'chat_history' not in st.session_state:
    st.session_state.chat_history = []
if 'session_notes' not in st.session_state:
    st.session_state.session_notes = ""

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def show_missing_dependency(feature_name, package_name):
    """Display a helpful message when a required package is missing"""
    st.error(f"❌ {feature_name} requires additional packages")
    st.code(f"pip install {package_name}", language="bash")
    st.info("💡 Contact your administrator to enable this feature")

def validate_domain(domain):
    """Validate domain name format"""
    if not domain:
        return False, "Domain name is required"
    
    domain = domain.replace('http://', '').replace('https://', '').split('/')[0]
    pattern = r'^(?:[a-zA-Z0-9](?:[a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,}$'
    if not re.match(pattern, domain):
        return False, "Invalid domain format"
    
    return True, domain

def validate_ip(ip):
    """Validate IP address format"""
    if not ip:
        return False, "IP address is required"
    
    pattern = r'^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$'
    if not re.match(pattern, ip):
        return False, "Invalid IP address format"
    
    return True, ip

def validate_email(email_addr):
    """Validate email address format"""
    if not email_addr:
        return False, "Email address is required"
    
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if not re.match(pattern, email_addr):
        return False, "Invalid email format"
    
    return True, email_addr

def create_session():
    """Create a requests session with retry logic"""
    session = requests.Session()
    retry = Retry(
        total=3,
        backoff_factor=0.3,
        status_forcelist=[500, 502, 503, 504]
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount('http://', adapter)
    session.mount('https://', adapter)
    session.headers.update({'User-Agent': CONFIG['user_agent']})
    return session

def safe_request(url, method='get', **kwargs):
    """Make a safe HTTP request with proper error handling"""
    try:
        session = create_session()
        kwargs.setdefault('timeout', CONFIG['request_timeout'])
        kwargs.setdefault('allow_redirects', True)
        
        if method.lower() == 'get':
            response = session.get(url, **kwargs)
        elif method.lower() == 'head':
            response = session.head(url, **kwargs)
        elif method.lower() == 'post':
            response = session.post(url, **kwargs)
        else:
            raise ValueError(f"Unsupported method: {method}")
        
        return True, response
    except requests.exceptions.Timeout:
        return False, "Request timed out"
    except requests.exceptions.ConnectionError:
        return False, "Connection error - unable to reach server"
    except requests.exceptions.TooManyRedirects:
        return False, "Too many redirects"
    except requests.exceptions.RequestException as e:
        return False, f"Request error: {str(e)}"
    except Exception as e:
        return False, f"Unexpected error: {str(e)}"

@st.cache_data(ttl=CONFIG['cache_ttl'])
def lookup_dns_record(domain, record_type='A'):
    """Lookup DNS records with caching"""
    if not DNS_AVAILABLE:
        return False, "DNS library not available"
    
    try:
        resolver = dns.resolver.Resolver()
        resolver.timeout = CONFIG['dns_timeout']
        resolver.lifetime = CONFIG['dns_timeout']
        
        answers = resolver.resolve(domain, record_type)
        results = [str(rdata) for rdata in answers]
        return True, results
    except dns.resolver.NXDOMAIN:
        return False, f"Domain {domain} does not exist"
    except dns.resolver.NoAnswer:
        return False, f"No {record_type} records found"
    except dns.resolver.Timeout:
        return False, "DNS query timed out"
    except Exception as e:
        return False, f"DNS error: {str(e)}"

@st.cache_data(ttl=CONFIG['cache_ttl'])
def lookup_whois(domain):
    """Lookup WHOIS information"""
    if not WHOIS_AVAILABLE:
        return False, "WHOIS library not available"
    
    try:
        w = whois.whois(domain)
        return True, w
    except Exception as e:
        return False, f"WHOIS error: {str(e)}"

def get_client_ip():
    """Get client's public IP address"""
    try:
        response = requests.get('https://api.ipify.org?format=json', timeout=5)
        return response.json()['ip']
    except:
        return "Unable to determine"

def check_password_strength(password):
    """Check password strength and provide feedback"""
    score = 0
    feedback = []
    
    if len(password) >= 8:
        score += 1
    else:
        feedback.append("Use at least 8 characters")
    
    if len(password) >= 12:
        score += 1
    
    if re.search(r'[a-z]', password):
        score += 1
    else:
        feedback.append("Add lowercase letters")
    
    if re.search(r'[A-Z]', password):
        score += 1
    else:
        feedback.append("Add uppercase letters")
    
    if re.search(r'\d', password):
        score += 1
    else:
        feedback.append("Add numbers")
    
    if re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
        score += 1
    else:
        feedback.append("Add special characters")
    
    if score <= 2:
        strength, color = "Weak", "error"
    elif score <= 4:
        strength, color = "Moderate", "warning"
    else:
        strength, color = "Strong", "success"
    
    return strength, score, feedback, color

# --- Specialized .ng Session & Utilities ---
ng_session = requests.Session()
ng_session.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
})

def query_ng_whois(domain):
    """Query WHOIS information for .ng domains via whois.net.ng"""
    url = "https://whois.net.ng/whois/"
    try:
        response = ng_session.get(url, params={"domain": domain}, timeout=10)
        return response.text
    except Exception as e:
        return f"Error: {e}"

def parse_ng_whois(html):
    """Parse .ng WHOIS HTML into structured sections"""
    soup = BeautifulSoup(html, 'html.parser')
    sections = {}
    cards = soup.find_all('div', class_='card mb-4')
    for card in cards:
        header = card.find('h5', class_='card-header whois_bg')
        if header:
            section_name = header.text.strip()
            data = {}
            table = card.find('table', class_='table')
            if table:
                for tr in table.find_all('tr'):
                    tds = tr.find_all('td')
                    if len(tds) == 2:
                        key = tds[0].text.strip().rstrip(':')
                        value = tds[1].get_text(separator=' ').strip()
                        data[key] = value
            sections[section_name] = data
    
    raw_pre = soup.find('pre')
    if raw_pre:
        sections['Raw Registry Data'] = raw_pre.get_text().strip()
    return sections

def get_live_ns(domain):
    """Fetch live NS records via Google DNS API"""
    try:
        url = f"https://dns.google/resolve?name={domain}&type=NS"
        res = requests.get(url, timeout=5).json()
        if res.get('Status') == 0 and 'Answer' in res:
            return [r['data'].lower().rstrip('.') for r in res['Answer'] if r['type'] == 2]
    except:
        pass
    return []

def get_dnssec_info(domain):
    """Neutral DNSSEC check - No icons, just info"""
    try:
        url = f"https://dns.google/resolve?name={domain}&type=DS"
        res = requests.get(url, timeout=5).json()
        return "DNSSEC Signed" if "Answer" in res else "DNSSEC Unsigned"
    except:
        return "DNSSEC Unknown"   

# ============================================================================
# SIDEBAR NAVIGATION
# ============================================================================

st.sidebar.title("🔧 Support Buddy")
st.sidebar.markdown("---")

category = st.sidebar.selectbox(
    "Select Category",
    [
        "🏠 Home",
        "👨‍💼 Admin Links",
        "🎫 Ticket Management",
        "🤖 AI Tools",
        "🌐 Domain & DNS",
        "📧 Email",
        "🌍 Web & HTTP",
        "📡 Network",
        "💾 Server & Database",
        "🛠️ Utilities"
    ]
)

# Tool selection based on category
if category == "🏠 Home":
    tool = "Home"
elif category == "👨‍💼 Admin Links":
    tool = st.sidebar.radio("Admin Tools", ["🔐 PIN Checker", "🔓 IP Unban", "📝 Bulk NS Updater", "📋 cPanel Account List"])
elif category == "🎫 Ticket Management":
    tool = st.sidebar.radio("Ticket Tools", ["✅ Support Ticket Checklist", "🔍 AI Ticket Analysis", "🩺 Smart Symptom Checker"])
elif category == "🤖 AI Tools":
    tool = st.sidebar.radio("AI Assistants", ["💬 AI Support Chat", "📧 AI Mail Error Assistant", "❓ Error Code Explainer"])
elif category == "🌐 Domain & DNS":
    tool = st.sidebar.radio("Domain Tools", ["🔍 Domain Status Check", "🔎 DNS Analyzer", "📋 NS Authority Checker", "🌍 WHOIS Lookup"])
elif category == "📧 Email":
    tool = st.sidebar.radio("Email Tools", ["📮 MX Record Checker", "✉️ Email Account Tester", "🔒 SPF/DKIM Check", "📄 Email Header Analyzer"])
elif category == "🌍 Web & HTTP":
    tool = st.sidebar.radio("Web Tools", ["🔧 Web Error Troubleshooting", "🔒 SSL Certificate Checker", "🔀 HTTPS Redirect Test", "⚠️ Mixed Content Detector", "📊 HTTP Status Code Checker", "🔗 Redirect Checker", "🤖 robots.txt Viewer", "⚡ Website Speed Test"])
elif category == "📡 Network":
    tool = st.sidebar.radio("Network Tools", ["🌐 My IP Address", "📡 Ping Tool", "🔌 Port Checker", "🗺️ Traceroute"])
elif category == "💾 Server & Database":
    tool = st.sidebar.radio("Server Tools", ["🗄️ MySQL Connection Tester", "📊 Database Size Calculator", "📁 FTP Connection Tester", "🔐 File Permission Checker"])
elif category == "🛠️ Utilities":
    tool = st.sidebar.radio("Utilities", ["📚 Help Center", "🔑 Password Strength Meter", "🌍 Timezone Converter", "📋 Copy-Paste Utilities", "📸 Screenshot Annotator", "📝 Session Notes", "🗑️ Clear Cache Instructions", "🧹 Flush DNS Cache"])

# ============================================================================
# MAIN CONTENT - TOOL IMPLEMENTATIONS
# ============================================================================

if tool == "Home":
    st.title("🏠 Welcome to Support Buddy")
    st.markdown("### Your Complete Technical Support Toolkit")
    st.markdown("Navigate using the sidebar to access over 40 support tools organized by category.")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown('<div class="info-box"><h4>🎫 Ticket Management</h4><p>Analyze tickets, check symptoms, gather information</p></div>', unsafe_allow_html=True)
    with col2:
        st.markdown('<div class="info-box"><h4>🤖 AI Tools</h4><p>Get instant help with AI-powered analysis</p></div>', unsafe_allow_html=True)
    with col3:
        st.markdown('<div class="info-box"><h4>🌐 Domain & DNS</h4><p>Check domain status, analyze DNS records</p></div>', unsafe_allow_html=True)
    
    st.markdown("---")
    st.markdown("### 📊 Feature Availability")
    
    col1, col2 = st.columns(2)
    with col1:
        st.metric("DNS Tools", "✅ Available" if FEATURES['dns'] else "⚠️ Limited")
        st.metric("Email Tools", "✅ Available" if FEATURES['email'] else "⚠️ Limited")
        st.metric("Database Tools", "✅ Available" if FEATURES['mysql'] else "⚠️ Limited")
    
    with col2:
        st.metric("WHOIS Lookup", "✅ Available" if FEATURES['whois'] else "⚠️ Limited")
        st.metric("FTP Testing", "✅ Available" if FEATURES['ftp'] else "⚠️ Limited")
        st.metric("AI Assistant", "✅ Available" if GEMINI_AVAILABLE else "⚠️ Configure API")

# ============================================================================
# PART: ADMIN TOOLS
# ============================================================================

elif tool == "🔐 PIN Checker":
    st.title("🔐 PIN Checker")
    st.markdown("Verify customer PINs for secure account access and verification.")
    
    col1, col2 = st.columns([3, 1])
    with col1:
        st.info("Check the provided customer PIN against the WHMCS records.")
    with col2:
        # Reverted to your original working link
        st.link_button("Open Tool", "https://my.hostafrica.com/admin/admin_tool/client-pin", use_container_width=True)

elif tool == "🔓 IP Unban":
    st.title("🔓 IP Unban")
    st.markdown("Search for and remove IP addresses from server firewalls.")
    
    col1, col2 = st.columns([3, 1])
    with col1:
        st.info("Use this to quickly unblock clients who are locked out.")
    with col2:
        st.link_button("Open Tool", "https://my.hostafrica.com/admin/custom/scripts/unban/", use_container_width=True)

elif tool == "📝 Bulk NS Updater":
    st.title("📝 Bulk Nameserver Updater")
    st.markdown("Update nameservers for multiple domains simultaneously in WHMCS.")
    
    col1, col2 = st.columns([3, 1])
    with col1:
        st.info("Save time by modifying NS records for domain batches.")
    with col2:
        st.link_button("🔄 Open Updater", "https://my.hostafrica.com/admin/addonmodules.php?module=nameserv_changer", use_container_width=True)

elif tool == "📋 cPanel Account List":
    st.title("📋 cPanel Account List")
    st.markdown("View a comprehensive list of all hosted cPanel accounts and their details.")
    
    col1, col2 = st.columns([3, 1])
    with col1:
        st.info("Access account status, package types, and owner details.")
    with col2:
        st.link_button("📂 Open List", "https://my.hostafrica.com/admin/custom/scripts/custom_tests/listaccounts.php", use_container_width=True)

# TICKET MANAGEMENT TOOLS
elif tool == "✅ Support Ticket Checklist":
    st.title("✅ Support Ticket Checklist")
    st.markdown("Ensure all necessary steps are completed for ticket resolution")
    
    checks = []
    
    st.markdown("### 📋 Basic Information")
    checks.append(st.checkbox("Customer verified (PIN/account check)"))
    checks.append(st.checkbox("Domain/service identified"))
    checks.append(st.checkbox("Issue clearly understood"))
    
    st.markdown("### 🔧 Technical Details")
    checks.append(st.checkbox("Error messages collected"))
    checks.append(st.checkbox("Screenshots/logs attached"))
    checks.append(st.checkbox("Steps to reproduce documented"))
    checks.append(st.checkbox("Affected services identified"))
    
    st.markdown("### 🔐 Account Access")
    checks.append(st.checkbox("Credentials verified (if needed)"))
    checks.append(st.checkbox("PIN checked and confirmed"))
    checks.append(st.checkbox("Access level appropriate"))
    
    st.markdown("### 🔍 Investigation")
    checks.append(st.checkbox("DNS records checked"))
    checks.append(st.checkbox("Server status verified"))
    checks.append(st.checkbox("Logs reviewed"))
    checks.append(st.checkbox("Recent changes identified"))
    
    st.markdown("### 📝 Response")
    checks.append(st.checkbox("Solution identified and tested"))
    checks.append(st.checkbox("Response drafted and reviewed"))
    checks.append(st.checkbox("Next steps documented"))
    checks.append(st.checkbox("Follow-up scheduled (if needed)"))
    
    completed = sum(checks)
    total = len(checks)
    progress = completed / total if total > 0 else 0
    
    st.markdown("---")
    st.progress(progress)
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Completed", f"{completed}/{total}")
    with col2:
        st.metric("Progress", f"{progress*100:.0f}%")
    with col3:
        if progress == 1.0:
            st.metric("Status", "✅ Ready")
        elif progress >= 0.7:
            st.metric("Status", "⚠️ Almost")
        else:
            st.metric("Status", "🔄 In Progress")

elif tool == "🔍 AI Ticket Analysis":
    st.title("🔍 AI Ticket Analysis")
    st.markdown("Let AI analyze support tickets and provide insights")
    
    if not GEMINI_AVAILABLE:
        st.error("⚠️ AI features require Gemini API key configuration")
        st.info("Contact your administrator to enable AI features")
    else:
        uploaded_file = st.file_uploader("Upload Screenshot:", type=['png', 'jpg', 'jpeg'])
        ticket_text = st.text_area("Or paste ticket text:", height=200, placeholder="Customer is experiencing...")
        
        if st.button("🔍 Analyze Ticket", type="primary"):
            if uploaded_file or ticket_text:
                with st.spinner("🤖 Analyzing ticket..."):
                    try:
                        model = genai.GenerativeModel('gemini-2.0-flash-exp')
                        prompt = """Analyze this support ticket and provide:
                        
1. **Issue Summary**: Brief description of the problem
2. **Category**: Type of issue (Email, Domain, Website, etc.)
3. **Severity**: Low/Medium/High/Critical
4. **Key Information**: Important details found
5. **Missing Information**: What else do we need?
6. **Troubleshooting Steps**: Specific steps to diagnose
7. **Recommended Tools**: Which Support Buddy tools to use
8. **Estimated Time**: How long this might take to resolve
9. **Potential Solutions**: Likely fixes

Be specific and actionable."""
                        
                        if uploaded_file:
                            image = Image.open(uploaded_file)
                            response = model.generate_content([prompt, image])
                        else:
                            response = model.generate_content(f"{prompt}\n\nTicket Content:\n{ticket_text}")
                        
                        st.markdown("### 🤖 AI Analysis:")
                        st.markdown(response.text)
                        
                    except Exception as e:
                        st.error(f"❌ Analysis failed: {str(e)}")
            else:
                st.warning("⚠️ Please provide either a screenshot or ticket text")

elif tool == "🩺 Smart Symptom Checker":
    st.title("🩺 Smart Symptom Checker")
    st.markdown("Diagnose issues based on symptoms")
    
    if not GEMINI_AVAILABLE:
        st.error("⚠️ AI features require Gemini API key configuration")
        st.info("Contact your administrator to enable AI features")
    else:
        symptom = st.text_area("Describe the issue:", height=150, placeholder="Website showing 500 error...")
        
        col1, col2 = st.columns(2)
        with col1:
            service = st.selectbox("Service Type:", ["Website", "Email", "Domain", "Database", "FTP", "SSL", "DNS", "Other"])
        with col2:
            when = st.selectbox("When started:", ["Just now", "Today", "Yesterday", "This week", "Over a week ago", "Unknown"])
        
        if st.button("🩺 Diagnose Issue", type="primary"):
            if symptom:
                with st.spinner("🤖 Diagnosing..."):
                    try:
                        model = genai.GenerativeModel('gemini-2.0-flash-exp')
                        prompt = f"""Diagnose this technical support issue:

**Symptoms**: {symptom}
**Service Type**: {service}
**Started**: {when}

Provide a comprehensive diagnosis with:

1. **Likely Causes** (ranked by probability)
2. **Immediate Checks** (quick things to verify)
3. **Recommended Support Buddy Tools** (specific tools to use)
4. **Step-by-Step Diagnosis Plan**
5. **Common Solutions** (what usually fixes this)
6. **Warning Signs for Escalation** (when to involve senior staff)
7. **Expected Resolution Time**

Be specific, technical, and actionable."""
                        
                        response = model.generate_content(prompt)
                        
                        st.markdown("### 🩺 Diagnosis Results:")
                        st.markdown(response.text)
                        
                    except Exception as e:
                        st.error(f"❌ Diagnosis failed: {str(e)}")
            else:
                st.warning("⚠️ Please describe the symptoms")

# AI TOOLS
elif tool == "💬 AI Support Chat":
    st.title("💬 AI Support Chat")
    st.markdown("Chat with AI assistant for instant support guidance")
    
    if not GEMINI_AVAILABLE:
        st.error("⚠️ AI features require Gemini API key configuration")
        st.info("Contact your administrator to enable AI features")
    else:
        # Display chat history
        for msg in st.session_state.chat_history:
            if msg['role'] == 'user':
                st.markdown(f'<div class="info-box">👤 **You:** {msg["content"]}</div>', unsafe_allow_html=True)
            else:
                st.markdown(f'<div class="success-box">🤖 **Assistant:** {msg["content"]}</div>', unsafe_allow_html=True)
        
        # Chat input
        user_input = st.text_area("Ask a question:", placeholder="How do I check if DNS is propagated?", key="chat_input")
        
        col1, col2 = st.columns([1, 4])
        with col1:
            if st.button("💬 Send", type="primary"):
                if user_input:
                    st.session_state.chat_history.append({'role': 'user', 'content': user_input})
                    
                    with st.spinner("🤖 Thinking..."):
                        try:
                            model = genai.GenerativeModel('gemini-2.0-flash-exp')
                            
                            context = """You are a technical support assistant for a web hosting company. 
                            Provide clear, helpful, step-by-step answers about:
                            - cPanel and web hosting
                            - DNS configuration and troubleshooting
                            - Email setup and issues
                            - Domain management
                            - SSL certificates
                            - Website errors (500, 403, 404, etc.)
                            - Database connections
                            - FTP access
                            
                            Always be specific, provide commands when relevant, and explain technical terms."""
                            
                            conversation = context + "\n\n" + "\n".join([
                                f"{'User' if m['role'] == 'user' else 'Assistant'}: {m['content']}" 
                                for m in st.session_state.chat_history[-10:]
                            ])
                            
                            response = model.generate_content(conversation)
                            st.session_state.chat_history.append({'role': 'assistant', 'content': response.text})
                            st.rerun()
                            
                        except Exception as e:
                            st.error(f"❌ Error: {str(e)}")
        
        with col2:
            if st.button("🗑️ Clear Chat"):
                st.session_state.chat_history = []
                st.rerun()

elif tool == "📧 AI Mail Error Assistant":
    st.title("📧 AI Mail Error Assistant")
    st.markdown("Analyze email error messages and get solutions")
    
    if not GEMINI_AVAILABLE:
        st.error("⚠️ AI features require Gemini API key configuration")
        st.info("Contact your administrator to enable AI features")
    else:
        error_msg = st.text_area("Email Error Message:", height=200, placeholder="550 5.1.1 User unknown...")
        
        if st.button("🔍 Analyze Error", type="primary"):
            if error_msg:
                with st.spinner("🤖 Analyzing error..."):
                    try:
                        model = genai.GenerativeModel('gemini-2.0-flash-exp')
                        prompt = f"""Analyze this email error message:

{error_msg}

Provide:

1. **Error Type**: What category of error is this?
2. **Plain English Explanation**: What does this mean to non-technical users?
3. **Root Cause**: What's actually causing this?
4. **Step-by-Step Solutions**: How to fix it (in order of likelihood)
5. **Prevention Tips**: How to avoid this in the future
6. **Related Tools**: Which Support Buddy tools can help diagnose/fix this

Be specific about server settings, DNS records, and authentication methods."""
                        
                        response = model.generate_content(prompt)
                        
                        st.markdown("### 🤖 Error Analysis:")
                        st.markdown(response.text)
                        
                    except Exception as e:
                        st.error(f"❌ Analysis failed: {str(e)}")
            else:
                st.warning("⚠️ Please paste an error message")

elif tool == "❓ Error Code Explainer":
    st.title("❓ Error Code Explainer")
    st.markdown("Get detailed explanations for error codes")
    
    if not GEMINI_AVAILABLE:
        st.error("⚠️ AI features require Gemini API key configuration")
        st.info("Contact your administrator to enable AI features")
    else:
        error_code = st.text_input("Error Code:", placeholder="500 Internal Server Error")
        context = st.text_area("Context (optional):", height=100, placeholder="User was uploading a file...")
        
        if st.button("🔍 Explain Error", type="primary"):
            if error_code:
                with st.spinner("🤖 Looking up error..."):
                    try:
                        model = genai.GenerativeModel('gemini-2.0-flash-exp')
                        prompt = f"""Explain this error code: {error_code}
{f"Context: {context}" if context else ""}

Provide:

1. **What It Means**: Clear explanation
2. **Common Causes**: Most frequent reasons for this error
3. **How to Fix**: Step-by-step troubleshooting
4. **How to Diagnose**: What to check and where
5. **Prevention**: How to avoid this error
6. **Related Errors**: Similar issues that might be confused with this

Be specific about web hosting environments, cPanel, and common server configurations."""
                        
                        response = model.generate_content(prompt)
                        
                        st.markdown("### 🤖 Error Explanation:")
                        st.markdown(response.text)
                        
                    except Exception as e:
                        st.error(f"❌ Lookup failed: {str(e)}")
            else:
                st.warning("⚠️ Please enter an error code")

# DOMAIN & DNS TOOLS
elif tool == "🔍 Domain Status Check":
    st.title("🔍 Domain Status Check")
    st.markdown("Check domain registration status and key DNS records")
    
    domain = st.text_input("Domain:", placeholder="example.com")
    
    if st.button("🔍 Check Status", type="primary"):
        if not domain:
            st.warning("⚠️ Please enter a domain name")
        else:
            valid, result = validate_domain(domain)
            if not valid:
                st.error(f"❌ {result}")
            else:
                domain = result
                
                with st.spinner(f"Checking {domain}..."):
                    if not DNS_AVAILABLE:
                        show_missing_dependency("DNS Check", "dnspython")
                    else:
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            st.markdown("### 🌐 A Records")
                            success, a_records = lookup_dns_record(domain, 'A')
                            if success:
                                for record in a_records:
                                    st.success(f"✅ {record}")
                            else:
                                st.error(f"❌ {a_records}")
                        
                        with col2:
                            st.markdown("### 📡 Name Servers")
                            success, ns_records = lookup_dns_record(domain, 'NS')
                            if success:
                                for record in ns_records:
                                    st.success(f"✅ {record}")
                            else:
                                st.error(f"❌ {ns_records}")
                        
                        st.markdown("### 📮 MX Records")
                        success, mx_records = lookup_dns_record(domain, 'MX')
                        if success:
                            for record in mx_records:
                                st.info(f"📧 {record}")
                        else:
                            st.warning(f"⚠️ {mx_records}")
                        
                        if WHOIS_AVAILABLE:
                            st.markdown("### 📋 WHOIS Information")
                            success, whois_data = lookup_whois(domain)
                            if success:
                                try:
                                    info_col1, info_col2 = st.columns(2)
                                    with info_col1:
                                        if hasattr(whois_data, 'registrar'):
                                            st.info(f"**Registrar:** {whois_data.registrar}")
                                        if hasattr(whois_data, 'creation_date'):
                                            st.info(f"**Created:** {whois_data.creation_date}")
                                    with info_col2:
                                        if hasattr(whois_data, 'expiration_date'):
                                            st.info(f"**Expires:** {whois_data.expiration_date}")
                                        if hasattr(whois_data, 'status'):
                                            st.info(f"**Status:** {whois_data.status}")
                                except Exception as e:
                                    st.warning(f"Could not parse all WHOIS data")
                            else:
                                st.warning(f"⚠️ {whois_data}")

elif tool == "🔎 DNS Analyzer":
    st.title("🔎 DNS Analyzer")
    st.markdown("Comprehensive DNS record analysis")
    
    domain = st.text_input("Domain:", placeholder="example.com")
    
    record_types = st.multiselect(
        "Record Types:",
        ['A', 'AAAA', 'MX', 'NS', 'TXT', 'CNAME', 'SOA'],
        default=['A', 'MX', 'NS']
    )
    
    if st.button("🔍 Analyze DNS", type="primary"):
        if not domain:
            st.warning("⚠️ Please enter a domain name")
        else:
            valid, result = validate_domain(domain)
            if not valid:
                st.error(f"❌ {result}")
            else:
                domain = result
                
                if not DNS_AVAILABLE:
                    show_missing_dependency("DNS Analysis", "dnspython")
                else:
                    with st.spinner(f"Analyzing DNS for {domain}..."):
                        results = {}
                        
                        for record_type in record_types:
                            success, records = lookup_dns_record(domain, record_type)
                            results[record_type] = {'success': success, 'data': records}
                        
                        for record_type, result in results.items():
                            st.markdown(f"### 📊 {record_type} Records")
                            if result['success']:
                                for record in result['data']:
                                    st.success(f"✅ {record}")
                            else:
                                st.error(f"❌ {result['data']}")
                            st.markdown("---")

elif tool == "📋 NS Authority Checker":
    st.title("📋 NS Authority Checker")
    st.markdown("Verify nameserver authority for domains")
    st.info("💡 Format: domain, ns1, ns2 (one per line)")
    
    input_text = st.text_area(
        "Domain and Nameservers:",
        placeholder="example.com, ns1.example.com, ns2.example.com",
        height=150
    )
    
    if st.button("🔍 Check Authority", type="primary"):
        if not input_text:
            st.warning("⚠️ Please enter domain and nameservers")
        else:
            if not DNS_AVAILABLE:
                show_missing_dependency("NS Authority Check", "dnspython")
            else:
                lines = [l.strip() for l in input_text.split('\n') if l.strip()]
                
                for line in lines:
                    parts = [p.strip() for p in line.split(',')]
                    if len(parts) < 2:
                        st.warning(f"⚠️ Invalid format: {line}")
                        continue
                    
                    domain = parts[0]
                    expected_ns = parts[1:]
                    
                    st.markdown(f"### Checking: {domain}")
                    
                    success, actual_ns = lookup_dns_record(domain, 'NS')
                    
                    if not success:
                        st.error(f"❌ Could not retrieve NS records: {actual_ns}")
                        continue
                    
                    actual_ns_normalized = [ns.rstrip('.').lower() for ns in actual_ns]
                    expected_ns_normalized = [ns.rstrip('.').lower() for ns in expected_ns]
                    
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.markdown("**Expected:**")
                        for ns in expected_ns:
                            st.code(ns)
                    
                    with col2:
                        st.markdown("**Actual:**")
                        for ns in actual_ns:
                            st.code(ns)
                    
                    all_match = all(ns in actual_ns_normalized for ns in expected_ns_normalized)
                    
                    if all_match:
                        st.success("✅ All nameservers match!")
                    else:
                        missing = [ns for ns in expected_ns_normalized if ns not in actual_ns_normalized]
                        st.error(f"❌ Mismatch detected. Missing: {', '.join(missing)}")
                    
                    st.markdown("---")

elif tool == "🌍 WHOIS Lookup":
    st.title("🌍 Advanced WHOIS & Domain Health")
    st.markdown("Detailed registration analysis with status-aware reporting.")
    
    domain_input = st.text_input("Enter domain name:", placeholder="example.com.ng", key="whois_main_input")
    
    if st.button("🔍 Analyze Domain", type="primary"):
        if domain_input:
            domain = domain_input.strip().lower().replace('https://', '').replace('http://', '').split('/')[0]
            
            with st.spinner(f"Analyzing {domain}..."):
                dnssec_text = check_dnssec_info(domain)
                ns_list = get_any_nameservers(domain)
                
                try:
                    # --- .ng UNIQUE TREATMENT ---
                    if domain.endswith('.ng'):
                        html_content = query_ng_whois(domain)
                        sections = parse_ng_whois(html_content)
                        reg_info = sections.get('Registration Info', {})
                        
                        status = reg_info.get('Domain Status', 'N/A').lower()
                        registrar = reg_info.get('Registrar', 'N/A')
                        
                        # .ng Status logic
                        if "ok" in status:
                            st.success(f"✅ Domain is healthy (Status: {status})")
                        else:
                            st.error(f"❌ Attention Required (Status: {status})")

                        # Display beautified HTML data
                        for section, data in sections.items():
                            with st.expander(f"📋 {section}", expanded=(section == 'Registration Info')):
                                for k, v in data.items():
                                    st.write(f"**{k}:** {v}")

                    # --- NON-.ng STANDARD TREATMENT ---
                    else:
                        w = whois.whois(domain)
                        registrar = w.registrar
                        # Logic for standard TLD status
                        raw_status = w.status[0] if isinstance(w.status, list) else w.status
                        status = str(raw_status).lower() if raw_status else "unknown"
                        
                        # Check expiration
                        is_expired = False
                        if w.expiration_date:
                            exp = w.expiration_date[0] if isinstance(w.expiration_date, list) else w.expiration_date
                            if exp < datetime.now():
                                is_expired = True

                        # Status Alerts
                        if any(x in status for x in ["hold", "suspended", "expired", "redemption"]) or is_expired:
                            st.error(f"❌ Domain Status Alert: {status.upper()}")
                        elif "ok" in status or "active" in status:
                            st.success(f"✅ Domain Status: OK")
                        else:
                            st.info(f"ℹ️ Status: {status}")

                        with st.expander("📄 Raw WHOIS Data"):
                            st.code(str(w), language=None)

                    # --- COMMON FOOTER (DNSSEC & NS) ---
                    st.markdown("---")
                    c1, c2 = st.columns(2)
                    with c1:
                        st.info(f"🛡️ {dnssec_text}")
                    with c2:
                        st.write("**Nameservers:**")
                        if ns_list:
                            for ns in ns_list:
                                st.write(f"- `{ns}`")
                        else:
                            st.warning("No nameservers found.")

                except Exception as e:
                    st.error(f"Analysis failed: {str(e)}")
        else:
            st.warning("⚠️ Please enter a domain name.")
            
# EMAIL TOOLS
elif tool == "📮 MX Record Checker":
    st.title("📮 MX Record Checker")
    st.markdown("Check mail exchanger records for a domain")
    
    domain = st.text_input("Domain:", placeholder="example.com")
    
    if st.button("🔍 Check MX Records", type="primary"):
        if not domain:
            st.warning("⚠️ Please enter a domain name")
        else:
            valid, result = validate_domain(domain)
            if not valid:
                st.error(f"❌ {result}")
            else:
                domain = result
                
                if not DNS_AVAILABLE:
                    show_missing_dependency("MX Record Check", "dnspython")
                else:
                    with st.spinner(f"Checking MX records for {domain}..."):
                        success, mx_records = lookup_dns_record(domain, 'MX')
                        
                        if not success:
                            st.error(f"❌ {mx_records}")
                        else:
                            st.success(f"✅ Found {len(mx_records)} MX record(s)")
                            
                            mx_data = []
                            for record in mx_records:
                                parts = str(record).split()
                                if len(parts) >= 2:
                                    priority = parts[0]
                                    hostname = ' '.join(parts[1:])
                                    mx_data.append({'Priority': priority, 'Mail Server': hostname})
                            
                            if mx_data:
                                df = pd.DataFrame(mx_data)
                                st.dataframe(df, use_container_width=True)
                                
                                st.markdown("### 🔌 Connectivity Test")
                                for mx in mx_data:
                                    hostname = mx['Mail Server'].rstrip('.')
                                    col1, col2 = st.columns([3, 1])
                                    with col1:
                                        st.code(hostname)
                                    with col2:
                                        try:
                                            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                                            sock.settimeout(5)
                                            result = sock.connect_ex((hostname, 25))
                                            sock.close()
                                            if result == 0:
                                                st.success("✅ Online")
                                            else:
                                                st.error("❌ Offline")
                                        except:
                                            st.warning("⚠️ Unknown")

elif tool == "✉️ Email Account Tester":
    st.title("✉️ Email Account Tester")
    st.warning("🔒 Security: Credentials are processed locally and never stored")
    st.markdown("Test IMAP and SMTP connections")
    
    col1, col2 = st.columns(2)
    
    with col1:
        email_addr = st.text_input("Email Address:", placeholder="user@example.com")
        imap_server = st.text_input("IMAP Server:", placeholder="mail.example.com")
        imap_port = st.number_input("IMAP Port:", value=993, min_value=1, max_value=65535)
        use_ssl_imap = st.checkbox("Use SSL (IMAP)", value=True)
    
    with col2:
        password = st.text_input("Password:", type="password")
        smtp_server = st.text_input("SMTP Server:", placeholder="mail.example.com")
        smtp_port = st.number_input("SMTP Port:", value=465, min_value=1, max_value=65535)
        use_ssl_smtp = st.checkbox("Use SSL (SMTP)", value=True)
    
    col_test1, col_test2 = st.columns(2)
    
    with col_test1:
        if st.button("🧪 Test IMAP", type="primary"):
            if not all([email_addr, password, imap_server]):
                st.warning("⚠️ Please fill in all IMAP fields")
            elif not IMAPLIB_AVAILABLE:
                show_missing_dependency("Email Testing", "built-in (should be available)")
            else:
                with st.spinner("Testing IMAP connection..."):
                    try:
                        if use_ssl_imap:
                            imap = imaplib.IMAP4_SSL(imap_server, imap_port)
                        else:
                            imap = imaplib.IMAP4(imap_server, imap_port)
                        
                        imap.login(email_addr, password)
                        st.success("✅ IMAP connection successful!")
                        
                        status, folders = imap.list()
                        if status == 'OK':
                            st.info(f"📁 Found {len(folders)} folder(s)")
                            with st.expander("View Folders"):
                                for folder in folders[:10]:
                                    st.code(folder.decode())
                        
                        imap.logout()
                    except imaplib.IMAP4.error as e:
                        st.error(f"❌ IMAP Error: {str(e)}")
                    except Exception as e:
                        st.error(f"❌ Connection failed: {str(e)}")

elif tool == "🔒 SPF/DKIM Check":
    st.title("🔒 SPF/DKIM/DMARC Check")
    st.markdown("Verify email authentication records")
    
    domain = st.text_input("Domain:", placeholder="example.com")
    
    if st.button("🔍 Check Email Authentication", type="primary"):
        if not domain:
            st.warning("⚠️ Please enter a domain name")
        else:
            valid, result = validate_domain(domain)
            if not valid:
                st.error(f"❌ {result}")
            else:
                domain = result
                
                if not DNS_AVAILABLE:
                    show_missing_dependency("Email Auth Check", "dnspython")
                else:
                    with st.spinner(f"Checking email authentication for {domain}..."):
                        st.markdown("### 🛡️ SPF (Sender Policy Framework)")
                        success, txt_records = lookup_dns_record(domain, 'TXT')
                        
                        spf_found = False
                        if success:
                            for record in txt_records:
                                if 'v=spf1' in record.lower():
                                    spf_found = True
                                    st.success("✅ SPF record found")
                                    st.code(record)
                                    
                                    if 'all' in record:
                                        if '-all' in record:
                                            st.success("✅ Hard fail (-all) - strict policy")
                                        elif '~all' in record:
                                            st.info("ℹ️ Soft fail (~all) - lenient policy")
                                        elif '?all' in record:
                                            st.warning("⚠️ Neutral (?all) - no policy")
                                        elif '+all' in record:
                                            st.error("❌ Pass all (+all) - insecure!")
                        
                        if not spf_found:
                            st.error("❌ No SPF record found")
                            st.info("💡 SPF records help prevent email spoofing")
                        
                        st.markdown("---")
                        
                        st.markdown("### 🔑 DKIM (DomainKeys Identified Mail)")
                        common_selectors = ['default', 'google', 'k1', 'selector1', 'selector2', 'dkim', 'mail']
                        dkim_found = False
                        
                        for selector in common_selectors:
                            dkim_domain = f"{selector}._domainkey.{domain}"
                            success, dkim_records = lookup_dns_record(dkim_domain, 'TXT')
                            if success:
                                for record in dkim_records:
                                    if 'v=DKIM1' in record or 'p=' in record:
                                        dkim_found = True
                                        st.success(f"✅ DKIM record found (selector: {selector})")
                                        st.code(record[:100] + "..." if len(record) > 100 else record)
                        
                        if not dkim_found:
                            st.warning("⚠️ No DKIM records found with common selectors")
                            st.info("💡 Try checking your email provider's documentation for the correct selector")
                        
                        st.markdown("---")
                        
                        st.markdown("### 📧 DMARC (Domain-based Message Authentication)")
                        dmarc_domain = f"_dmarc.{domain}"
                        success, dmarc_records = lookup_dns_record(dmarc_domain, 'TXT')
                        
                        dmarc_found = False
                        if success:
                            for record in dmarc_records:
                                if 'v=DMARC1' in record:
                                    dmarc_found = True
                                    st.success("✅ DMARC record found")
                                    st.code(record)
                                    
                                    if 'p=reject' in record.lower():
                                        st.success("✅ Reject policy - maximum protection")
                                    elif 'p=quarantine' in record.lower():
                                        st.info("ℹ️ Quarantine policy - moderate protection")
                                    elif 'p=none' in record.lower():
                                        st.warning("⚠️ Monitor only policy - minimal protection")
                        
                        if not dmarc_found:
                            st.error("❌ No DMARC record found")
                            st.info("💡 DMARC helps protect against email spoofing and phishing")
                        
                        st.markdown("---")
                        st.markdown("### 📊 Overall Assessment")
                        
                        scores = {'SPF': spf_found, 'DKIM': dkim_found, 'DMARC': dmarc_found}
                        enabled = sum(scores.values())
                        total = len(scores)
                        
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            st.metric("SPF", "✅" if scores['SPF'] else "❌")
                        with col2:
                            st.metric("DKIM", "✅" if scores['DKIM'] else "❌")
                        with col3:
                            st.metric("DMARC", "✅" if scores['DMARC'] else "❌")
                        
                        if enabled == total:
                            st.success("🎉 Excellent! All email authentication methods are configured")
                        elif enabled >= 2:
                            st.info(f"✓ Good! {enabled}/{total} authentication methods configured")
                        else:
                            st.warning(f"⚠️ Only {enabled}/{total} authentication methods configured")

elif tool == "📄 Email Header Analyzer":
    st.title("📄 Email Header Analyzer")
    st.markdown("Analyze email headers to troubleshoot delivery issues")
    
    headers = st.text_area("Paste Email Headers:", height=300, placeholder="Received: from...\nFrom:...\nTo:...")
    
    if st.button("🔍 Analyze Headers", type="primary"):
        if not headers:
            st.warning("⚠️ Please paste email headers")
        else:
            with st.spinner("Analyzing headers..."):
                lines = headers.split('\n')
                
                parsed_headers = {}
                current_key = None
                current_value = []
                
                for line in lines:
                    if ':' in line and not line.startswith((' ', '\t')):
                        if current_key:
                            parsed_headers[current_key] = '\n'.join(current_value)
                        parts = line.split(':', 1)
                        current_key = parts[0].strip()
                        current_value = [parts[1].strip()] if len(parts) > 1 else []
                    elif current_key and line.strip():
                        current_value.append(line.strip())
                
                if current_key:
                    parsed_headers[current_key] = '\n'.join(current_value)
                
                st.success(f"✅ Parsed {len(parsed_headers)} header fields")
                
                tab1, tab2, tab3 = st.tabs(["📬 Basic Info", "🔀 Routing", "🔍 All Headers"])
                
                with tab1:
                    st.markdown("### Basic Information")
                    key_headers = ['From', 'To', 'Subject', 'Date', 'Message-ID']
                    for header in key_headers:
                        if header in parsed_headers:
                            st.info(f"**{header}:** {parsed_headers[header]}")
                
                with tab2:
                    st.markdown("### Email Route")
                    received_headers = [v for k, v in parsed_headers.items() if k.lower() == 'received']
                    if received_headers:
                        st.info(f"📍 {len(received_headers)} hop(s) detected")
                        for i, received in enumerate(reversed(received_headers), 1):
                            with st.expander(f"Hop {i}"):
                                st.code(received)
                    else:
                        st.warning("No Received headers found")
                    
                    auth_headers = ['Authentication-Results', 'Received-SPF', 'DKIM-Signature']
                    st.markdown("### Authentication Results")
                    for header in auth_headers:
                        if header in parsed_headers:
                            st.code(f"{header}: {parsed_headers[header]}")
                
                with tab3:
                    st.markdown("### All Headers")
                    for key, value in parsed_headers.items():
                        with st.expander(f"📋 {key}"):
                            st.code(value)

# WEB & HTTP TOOLS
elif tool == "🔧 Web Error Troubleshooting":
    st.title("🔧 Web Error Troubleshooting")
    st.markdown("Quick guides for common web errors")
    
    error = st.selectbox("Select Error:", [
        "500 Internal Server Error",
        "503 Service Unavailable",
        "404 Not Found",
        "403 Forbidden",
        "502 Bad Gateway",
        "504 Gateway Timeout"
    ])
    
    if error == "500 Internal Server Error":
        st.markdown("""
        ### 500 Internal Server Error
        
        **Common Causes:**
        - PHP syntax errors or fatal errors
        - Incorrect .htaccess directives
        - Incorrect file permissions (should be 644 for files, 755 for directories)
        - PHP memory limit exceeded
        - Missing PHP modules
        
        **Troubleshooting Steps:**
        1. **Check error logs** - Look in cPanel → Errors or /home/user/public_html/error_log
        2. **Test .htaccess** - Rename to .htaccess.bak to disable
        3. **Check permissions** - Files: 644, Folders: 755
        4. **Review recent changes** - What was changed before error started?
        5. **Test PHP** - Create info.php with <?php phpinfo(); ?>
        
        **Quick Fixes:**
        - Increase PHP memory limit in php.ini or .htaccess
        - Fix syntax errors shown in error logs
        - Restore from backup if recent change caused issue
        """)
    
    elif error == "503 Service Unavailable":
        st.markdown("""
        ### 503 Service Unavailable
        
        **Common Causes:**
        - Server overload or resource limits hit
        - Maintenance mode enabled
        - PHP-FPM not running
        - Too many concurrent connections
        
        **Troubleshooting Steps:**
        1. Check if maintenance mode is on
        2. Review server load and resource usage
        3. Check if PHP-FPM is running
        4. Look for DDoS or traffic spikes
        5. Check error logs for details
        
        **Quick Fixes:**
        - Restart PHP-FPM
        - Disable maintenance mode
        - Increase resource limits
        - Enable caching
        """)
    
    elif error == "404 Not Found":
        st.markdown("""
        ### 404 Not Found
        
        **Common Causes:**
        - File or page doesn't exist
        - Incorrect URL or broken link
        - Permalink/rewrite rules issue
        - Case sensitivity (Linux servers)
        
        **Troubleshooting Steps:**
        1. Verify file exists in correct location
        2. Check URL spelling and case
        3. Test permalink structure
        4. Review .htaccess rewrite rules
        5. Check document root setting
        
        **Quick Fixes:**
        - Upload missing files
        - Fix broken links
        - Reset permalinks (WordPress)
        - Check .htaccess mod_rewrite rules
        """)
    
    elif error == "403 Forbidden":
        st.markdown("""
        ### 403 Forbidden
        
        **Common Causes:**
        - Incorrect file/folder permissions
        - Missing index file
        - .htaccess blocking access
        - IP blocked by firewall
        - Directory browsing disabled
        
        **Troubleshooting Steps:**
        1. **Check permissions** - Files: 644, Folders: 755
        2. **Verify index file** - index.html, index.php must exist
        3. **Review .htaccess** - Look for deny/allow rules
        4. **Check firewall** - Verify IP not blocked
        5. **Test file ownership** - Should match cPanel user
        
        **Quick Fixes:**
        - Fix permissions: chmod 644 files, chmod 755 folders
        - Create index file
        - Remove blocking rules from .htaccess
        - Unblock IP from firewall
        """)
    
    elif error == "502 Bad Gateway":
        st.markdown("""
        ### 502 Bad Gateway
        
        **Common Causes:**
        - PHP-FPM crashed or not responding
        - Backend server timeout
        - Firewall blocking connections
        - Server overload
        
        **Troubleshooting Steps:**
        1. Check PHP-FPM status
        2. Review error logs
        3. Check server resources
        4. Test backend connectivity
        5. Review recent changes
        
        **Quick Fixes:**
        - Restart PHP-FPM
        - Increase timeout limits
        - Check server load
        - Disable problematic plugins
        """)
    
    elif error == "504 Gateway Timeout":
        st.markdown("""
        ### 504 Gateway Timeout
        
        **Common Causes:**
        - Slow database queries
        - PHP script timeout
        - Server overload
        - External API delays
        
        **Troubleshooting Steps:**
        1. Check database performance
        2. Review slow query logs
        3. Test PHP execution time
        4. Check external service status
        5. Monitor server resources
        
        **Quick Fixes:**
        - Optimize database queries
        - Increase PHP max_execution_time
        - Enable caching
        - Optimize scripts
        """)

elif tool == "🔒 SSL Certificate Checker":
    st.title("🔒 SSL Certificate Checker")
    st.markdown("Check SSL/TLS certificate status")
    
    domain = st.text_input("Domain:", placeholder="example.com")
    
    if st.button("🔍 Check SSL Certificate", type="primary"):
        if not domain:
            st.warning("⚠️ Please enter a domain name")
        else:
            valid, result = validate_domain(domain)
            if not valid:
                st.error(f"❌ {result}")
            else:
                domain = result
                
                with st.spinner(f"Checking SSL for {domain}..."):
                    try:
                        context = ssl.create_default_context()
                        with socket.create_connection((domain, 443), timeout=10) as sock:
                            with context.wrap_socket(sock, server_hostname=domain) as ssock:
                                cert = ssock.getpeercert()
                                
                                st.success("✅ SSL Certificate found and valid")
                                
                                col1, col2 = st.columns(2)
                                
                                with col1:
                                    st.info(f"**Issuer:** {dict(x[0] for x in cert['issuer'])['organizationName']}")
                                    st.info(f"**Subject:** {dict(x[0] for x in cert['subject'])['commonName']}")
                                
                                with col2:
                                    st.info(f"**Valid From:** {cert['notBefore']}")
                                    st.info(f"**Valid Until:** {cert['notAfter']}")
                                
                                if 'subjectAltName' in cert:
                                    st.markdown("### 📜 Subject Alternative Names")
                                    for alt_name in cert['subjectAltName']:
                                        st.code(alt_name[1])
                                
                    except ssl.SSLError as e:
                        st.error(f"❌ SSL Error: {str(e)}")
                    except socket.gaierror:
                        st.error("❌ Could not resolve domain")
                    except socket.timeout:
                        st.error("❌ Connection timed out")
                    except Exception as e:
                        st.error(f"❌ Error: {str(e)}")

elif tool == "🔀 HTTPS Redirect Test":
    st.title("🔀 HTTPS Redirect Test")
    st.markdown("Test if HTTP redirects to HTTPS")
    
    domain = st.text_input("Domain:", placeholder="example.com")
    
    if st.button("🔍 Test Redirect", type="primary"):
        if not domain:
            st.warning("⚠️ Please enter a domain name")
        else:
            valid, result = validate_domain(domain)
            if not valid:
                st.error(f"❌ {result}")
            else:
                domain = result
                url = f"http://{domain}"
                
                with st.spinner(f"Testing redirect for {domain}..."):
                    success, response = safe_request(url)
                    
                    if not success:
                        st.error(f"❌ {response}")
                    else:
                        if response.url.startswith('https://'):
                            st.success("✅ HTTP redirects to HTTPS correctly")
                            st.info(f"**Final URL:** {response.url}")
                            
                            if len(response.history) > 0:
                                st.markdown("### Redirect Chain:")
                                for i, resp in enumerate(response.history, 1):
                                    st.code(f"{i}. {resp.url} → {resp.status_code}")
                        else:
                            st.error("❌ No HTTPS redirect found")
                            st.warning("⚠️ Consider adding HTTPS redirect in .htaccess")
                            st.code("""RewriteEngine On
RewriteCond %{HTTPS} off
RewriteRule ^(.*)$ https://%{HTTP_HOST}%{REQUEST_URI} [L,R=301]""", language="apache")

elif tool == "⚠️ Mixed Content Detector":
    st.title("⚠️ Mixed Content Detector")
    st.markdown("Scan for HTTP resources on HTTPS pages")
    
    url = st.text_input("URL:", placeholder="https://example.com")
    
    if st.button("🔍 Scan for Mixed Content", type="primary"):
        if not url:
            st.warning("⚠️ Please enter a URL")
        elif not url.startswith('http'):
            st.error("❌ URL must include protocol (http:// or https://)")
        else:
            with st.spinner(f"Scanning {url}..."):
                success, response = safe_request(url)
                
                if not success:
                    st.error(f"❌ {response}")
                else:
                    http_count = response.text.count('http://')
                    https_count = response.text.count('https://')
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        st.metric("HTTP Resources", http_count)
                    with col2:
                        st.metric("HTTPS Resources", https_count)
                    
                    if http_count > 0:
                        st.warning(f"⚠️ Found {http_count} HTTP resources that should be HTTPS")
                        st.info("💡 Mixed content can cause browser warnings and security issues")
                    else:
                        st.success("✅ No mixed content detected")

elif tool == "📊 HTTP Status Code Checker":
    st.title("📊 HTTP Status Code Checker")
    st.markdown("Check HTTP response status codes")
    
    url = st.text_input("URL:", placeholder="https://example.com")
    
    if st.button("🔍 Check Status", type="primary"):
        if not url:
            st.warning("⚠️ Please enter a URL")
        elif not url.startswith('http'):
            st.error("❌ URL must include protocol (http:// or https://)")
        else:
            with st.spinner(f"Checking {url}..."):
                success, response = safe_request(url, method='head')
                
                if not success:
                    st.error(f"❌ {response}")
                else:
                    code = response.status_code
                    
                    if 200 <= code < 300:
                        st.success(f"✅ Status: {code} {response.reason}")
                    elif 300 <= code < 400:
                        st.info(f"🔀 Status: {code} {response.reason} (Redirect)")
                    elif 400 <= code < 500:
                        st.warning(f"⚠️ Status: {code} {response.reason} (Client Error)")
                    else:
                        st.error(f"❌ Status: {code} {response.reason} (Server Error)")
                    
                    st.markdown("### Response Headers:")
                    for key, value in response.headers.items():
                        st.code(f"{key}: {value}")

elif tool == "🔗 Redirect Checker":
    st.title("🔗 Redirect Checker")
    st.markdown("Track redirect chains")
    
    url = st.text_input("URL:", placeholder="https://example.com")
    
    if st.button("🔍 Check Redirects", type="primary"):
        if not url:
            st.warning("⚠️ Please enter a URL")
        elif not url.startswith('http'):
            st.error("❌ URL must include protocol")
        else:
            with st.spinner(f"Following redirects for {url}..."):
                success, response = safe_request(url)
                
                if not success:
                    st.error(f"❌ {response}")
                else:
                    if response.history:
                        st.success(f"✅ {len(response.history)} redirect(s) found")
                        
                        st.markdown("### Redirect Chain:")
                        for i, r in enumerate(response.history, 1):
                            col1, col2 = st.columns([4, 1])
                            with col1:
                                st.code(r.url)
                            with col2:
                                st.code(r.status_code)
                        
                        st.markdown("### Final Destination:")
                        st.code(response.url)
                    else:
                        st.info("ℹ️ No redirects - page loads directly")
                        st.code(response.url)

elif tool == "🤖 robots.txt Viewer":
    st.title("🤖 robots.txt Viewer")
    st.markdown("View and analyze robots.txt files")
    
    domain = st.text_input("Domain:", placeholder="example.com")
    
    if st.button("🔍 Fetch robots.txt", type="primary"):
        if not domain:
            st.warning("⚠️ Please enter a domain name")
        else:
            valid, result = validate_domain(domain)
            if not valid:
                st.error(f"❌ {result}")
            else:
                domain = result
                url = f"https://{domain}/robots.txt"
                
                with st.spinner(f"Fetching robots.txt from {domain}..."):
                    success, response = safe_request(url)
                    
                    if not success:
                        st.error(f"❌ {response}")
                    elif response.status_code == 200:
                        st.success("✅ robots.txt found")
                        st.code(response.text, language="text")
                        
                        lines = response.text.split('\n')
                        user_agents = [l for l in lines if l.startswith('User-agent:')]
                        disallows = [l for l in lines if l.startswith('Disallow:')]
                        
                        col1, col2 = st.columns(2)
                        with col1:
                            st.metric("User-Agents", len(user_agents))
                        with col2:
                            st.metric("Disallow Rules", len(disallows))
                    else:
                        st.warning(f"⚠️ robots.txt not found ({response.status_code})")

elif tool == "⚡ Website Speed Test":
    st.title("⚡ Website Speed Test")
    st.markdown("Test website loading speed")
    
    url = st.text_input("URL:", placeholder="https://example.com")
    
    if st.button("⚡ Test Speed", type="primary"):
        if not url:
            st.warning("⚠️ Please enter a URL")
        elif not url.startswith('http'):
            st.error("❌ URL must include protocol")
        else:
            with st.spinner(f"Testing speed for {url}..."):
                start_time = time.time()
                success, response = safe_request(url)
                load_time = time.time() - start_time
                
                if not success:
                    st.error(f"❌ {response}")
                else:
                    col1, col2, col3 = st.columns(3)
                    
                    with col1:
                        st.metric("Load Time", f"{load_time:.2f}s")
                    with col2:
                        size_kb = len(response.content) / 1024
                        st.metric("Page Size", f"{size_kb:.2f} KB")
                    with col3:
                        st.metric("Status", response.status_code)
                    
                    if load_time < 1:
                        st.success("✅ Excellent - Very Fast!")
                    elif load_time < 3:
                        st.success("✅ Good - Fast enough")
                    elif load_time < 5:
                        st.warning("⚠️ Moderate - Could be faster")
                    else:
                        st.error("❌ Slow - Optimization needed")

# NETWORK TOOLS
elif tool == "🌐 My IP Address":
    st.title("🌐 My IP Address")
    ip = get_client_ip()
    st.markdown(f'<div class="success-box"><h2 style="text-align:center">{ip}</h2></div>', unsafe_allow_html=True)
    
    if ip != "Unable to determine":
        st.info("💡 This is your public IP address")

elif tool == "📡 Ping Tool":
    st.title("📡 Ping Tool")
    st.markdown("Test network connectivity")
    st.warning("⚠️ Ping may not work on some cloud platforms (e.g., Streamlit Cloud)")
    
    hostname = st.text_input("Hostname or IP:", placeholder="example.com or 8.8.8.8")
    count = st.slider("Number of pings:", 1, 10, 4)
    
    if st.button("📡 Ping", type="primary"):
        if not hostname:
            st.warning("⚠️ Please enter a hostname or IP")
        else:
            param = '-n' if platform.system().lower() == 'windows' else '-c'
            
            with st.spinner(f"Pinging {hostname}..."):
                try:
                    result = subprocess.run(
                        ['ping', param, str(count), hostname],
                        capture_output=True,
                        text=True,
                        timeout=30
                    )
                    
                    if result.returncode == 0:
                        st.success("✅ Ping successful")
                    else:
                        st.error("❌ Ping failed")
                    
                    st.code(result.stdout)
                    
                except subprocess.TimeoutExpired:
                    st.error("❌ Ping timed out")
                except FileNotFoundError:
                    st.error("❌ Ping command not available on this system")
                except Exception as e:
                    st.error(f"❌ Error: {str(e)}")

elif tool == "🔌 Port Checker":
    st.title("🔌 Port Checker")
    st.markdown("Check if a port is open")
    
    col1, col2 = st.columns(2)
    
    with col1:
        host = st.text_input("Host:", placeholder="example.com or 192.168.1.1")
    with col2:
        port = st.number_input("Port:", min_value=1, max_value=65535, value=80)
    
    common_ports = {
        'HTTP': 80,
        'HTTPS': 443,
        'FTP': 21,
        'SSH': 22,
        'SMTP': 25,
        'MySQL': 3306,
        'cPanel': 2083
    }
    
    st.markdown("**Common Ports:**")
    port_cols = st.columns(len(common_ports))
    for i, (name, port_num) in enumerate(common_ports.items()):
        with port_cols[i]:
            if st.button(f"{name} ({port_num})"):
                port = port_num
    
    if st.button("🔌 Check Port", type="primary"):
        if not host:
            st.warning("⚠️ Please enter a host")
        else:
            with st.spinner(f"Checking port {port} on {host}..."):
                try:
                    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    sock.settimeout(5)
                    result = sock.connect_ex((host, int(port)))
                    sock.close()
                    
                    if result == 0:
                        st.success(f"✅ Port {port} is OPEN on {host}")
                    else:
                        st.error(f"❌ Port {port} is CLOSED or filtered on {host}")
                        
                except socket.gaierror:
                    st.error("❌ Could not resolve hostname")
                except socket.timeout:
                    st.error("❌ Connection timed out")
                except Exception as e:
                    st.error(f"❌ Error: {str(e)}")
    
    with col_test2:
        if st.button("🧪 Test SMTP", type="primary"):
            if not all([email_addr, password, smtp_server]):
                st.warning("⚠️ Please fill in all SMTP fields")
            elif not SMTPLIB_AVAILABLE:
                show_missing_dependency("Email Testing", "built-in (should be available)")
            else:
                with st.spinner("Testing SMTP connection..."):
                    try:
                        if use_ssl_smtp:
                            smtp = smtplib.SMTP_SSL(smtp_server, smtp_port)
                        else:
                            smtp = smtplib.SMTP(smtp_server, smtp_port)
                            smtp.starttls()
                        
                        smtp.login(email_addr, password)
                        st.success("✅ SMTP connection successful!")
                        st.info("📤 Account can send emails")
                        smtp.quit()
                    except smtplib.SMTPAuthenticationError:
                        st.error("❌ Authentication failed - check email/password")
                    except smtplib.SMTPException as e:
                        st.error(f"❌ SMTP Error: {str(e)}")
                    except Exception as e:
                        st.error(f"❌ Connection failed: {str(e)}")
                        st.info("💡 Check your connection details and try again")

elif tool == "🗺️ Traceroute":
    st.title("🗺️ Traceroute")
    st.markdown("Trace the route packets take to reach a host")
    st.warning("⚠️ Traceroute may not work on some cloud platforms (e.g., Streamlit Cloud)")
    
    hostname = st.text_input("Hostname or IP:", placeholder="example.com")
    
    if st.button("🗺️ Trace Route", type="primary"):
        if not hostname:
            st.warning("⚠️ Please enter a hostname or IP")
        else:
            st.info("⏳ Traceroute may take up to a minute...")
            
            with st.spinner(f"Tracing route to {hostname}..."):
                try:
                    if platform.system().lower() == 'windows':
                        cmd = ['tracert', '-d', '-w', '1000', hostname]
                    else:
                        cmd = ['traceroute', '-m', '15', '-w', '2', hostname]
                    
                    result = subprocess.run(
                        cmd,
                        capture_output=True,
                        text=True,
                        timeout=60
                    )
                    
                    st.success("✅ Traceroute complete")
                    st.code(result.stdout)
                    
                except subprocess.TimeoutExpired:
                    st.error("❌ Traceroute timed out")
                except FileNotFoundError:
                    st.error("❌ Traceroute command not available on this system")
                except Exception as e:
                    st.error(f"❌ Error: {str(e)}")

# SERVER & DATABASE TOOLS
elif tool == "🗄️ MySQL Connection Tester":
    st.title("🗄️ MySQL Connection Tester")
    st.warning("🔒 Security: Credentials are processed locally and never stored")
    st.markdown("Test MySQL/MariaDB database connections")
    
    col1, col2 = st.columns(2)
    
    with col1:
        host = st.text_input("Host:", placeholder="localhost")
        db = st.text_input("Database:", placeholder="mydatabase")
        port = st.number_input("Port:", value=3306, min_value=1, max_value=65535)
    
    with col2:
        user = st.text_input("Username:", placeholder="dbuser")
        pwd = st.text_input("Password:", type="password")
    
    if st.button("🧪 Test Connection", type="primary"):
        if not all([host, user, pwd, db]):
            st.warning("⚠️ Please fill in all fields")
        else:
            if not MYSQL_AVAILABLE:
                show_missing_dependency("MySQL Testing", "pymysql")
            else:
                with st.spinner("Testing MySQL connection..."):
                    try:
                        connection = pymysql.connect(
                            host=host,
                            user=user,
                            password=pwd,
                            database=db,
                            port=port,
                            connect_timeout=10
                        )
                        
                        st.success("✅ Connection successful!")
                        
                        cursor = connection.cursor()
                        cursor.execute("SELECT VERSION()")
                        version = cursor.fetchone()
                        st.info(f"📊 MySQL Version: {version[0]}")
                        
                        cursor.execute(f"""
                            SELECT 
                                ROUND(SUM(data_length + index_length) / 1024 / 1024, 2) AS 'Size (MB)'
                            FROM information_schema.TABLES
                            WHERE table_schema = '{db}'
                        """)
                        size = cursor.fetchone()
                        if size and size[0]:
                            st.info(f"💾 Database Size: {size[0]} MB")
                        
                        cursor.execute(f"SHOW TABLES FROM {db}")
                        tables = cursor.fetchall()
                        if tables:
                            st.success(f"📋 Found {len(tables)} table(s)")
                            with st.expander("View Tables"):
                                for table in tables:
                                    st.code(table[0])
                        
                        cursor.close()
                        connection.close()
                        
                    except pymysql.err.OperationalError as e:
                        error_code = e.args[0]
                        if error_code == 1045:
                            st.error("❌ Access denied - check username/password")
                        elif error_code == 2003:
                            st.error("❌ Can't connect to MySQL server - check host/port")
                        elif error_code == 1049:
                            st.error(f"❌ Unknown database '{db}'")
                        else:
                            st.error(f"❌ MySQL Error ({error_code}): {e.args[1]}")
                    except Exception as e:
                        st.error(f"❌ Connection failed: {str(e)}")

elif tool == "📊 Database Size Calculator":
    st.title("📊 Database Size Calculator")
    st.markdown("Calculate and convert database sizes")
    
    tab1, tab2 = st.tabs(["🔢 Size Converter", "📋 SQL Query"])
    
    with tab1:
        col1, col2 = st.columns(2)
        
        with col1:
            size = st.number_input("Size:", value=1024.0, min_value=0.0)
            unit = st.selectbox("Unit:", ["Bytes", "KB", "MB", "GB", "TB"])
        
        multipliers = {"Bytes": 1, "KB": 1024, "MB": 1024**2, "GB": 1024**3, "TB": 1024**4}
        size_bytes = size * multipliers[unit]
        
        with col2:
            st.markdown("### Conversions")
            st.metric("Bytes", f"{size_bytes:,.0f}")
            st.metric("KB", f"{size_bytes/1024:,.2f}")
            st.metric("MB", f"{size_bytes/(1024**2):,.2f}")
            st.metric("GB", f"{size_bytes/(1024**3):,.4f}")
            st.metric("TB", f"{size_bytes/(1024**4):,.6f}")
        
        st.markdown("---")
        st.markdown("### 📏 Size References")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.info("**Small DB**\n< 100 MB")
        with col2:
            st.info("**Medium DB**\n100 MB - 10 GB")
        with col3:
            st.info("**Large DB**\n> 10 GB")
    
    with tab2:
        st.markdown("### SQL Queries for Size Checking")
        
        st.markdown("**All Databases:**")
        st.code("""SELECT 
    table_schema AS 'Database',
    ROUND(SUM(data_length + index_length) / 1024 / 1024, 2) AS 'Size (MB)'
FROM information_schema.TABLES
GROUP BY table_schema
ORDER BY SUM(data_length + index_length) DESC;""", language="sql")
        
        st.markdown("**Specific Database:**")
        db_name = st.text_input("Database name:", placeholder="mydatabase")
        if db_name:
            st.code(f"""SELECT 
    table_name AS 'Table',
    ROUND(((data_length + index_length) / 1024 / 1024), 2) AS 'Size (MB)'
FROM information_schema.TABLES
WHERE table_schema = '{db_name}'
ORDER BY (data_length + index_length) DESC;""", language="sql")

elif tool == "📁 FTP Connection Tester":
    st.title("📁 FTP Connection Tester")
    st.warning("🔒 Security: Credentials are processed locally and never stored")
    st.markdown("Test FTP/FTPS connections")
    
    col1, col2 = st.columns(2)
    
    with col1:
        ftp_host = st.text_input("Host:", placeholder="ftp.example.com")
        ftp_user = st.text_input("Username:", placeholder="ftpuser")
    
    with col2:
        ftp_pass = st.text_input("Password:", type="password")
        ftp_port = st.number_input("Port:", value=21, min_value=1, max_value=65535)
    
    use_tls = st.checkbox("Use TLS (FTPS)", value=False)
    
    if st.button("🧪 Test FTP Connection", type="primary"):
        if not all([ftp_host, ftp_user, ftp_pass]):
            st.warning("⚠️ Please fill in all fields")
        else:
            if not FTPLIB_AVAILABLE:
                show_missing_dependency("FTP Testing", "built-in (should be available)")
            else:
                with st.spinner("Testing FTP connection..."):
                    try:
                        if use_tls:
                            ftp = ftplib.FTP_TLS()
                        else:
                            ftp = ftplib.FTP()
                        
                        ftp.connect(ftp_host, ftp_port, timeout=10)
                        st.info("📡 Connected to server")
                        
                        ftp.login(ftp_user, ftp_pass)
                        st.success("✅ Login successful!")
                        
                        if use_tls:
                            ftp.prot_p()
                            st.info("🔒 Secure data channel enabled")
                        
                        welcome = ftp.getwelcome()
                        if welcome:
                            st.info(f"💬 Server: {welcome}")
                        
                        current_dir = ftp.pwd()
                        st.info(f"📂 Current directory: {current_dir}")
                        
                        try:
                            files = []
                            ftp.retrlines('LIST', files.append)
                            if files:
                                st.success(f"📋 Found {len(files)} item(s)")
                                with st.expander("View Directory Listing"):
                                    for file in files[:20]:
                                        st.code(file)
                                    if len(files) > 20:
                                        st.info(f"... and {len(files) - 20} more")
                        except Exception as e:
                            st.warning(f"⚠️ Could not list directory: {e}")
                        
                        ftp.quit()
                        
                    except ftplib.error_perm as e:
                        error_msg = str(e)
                        if '530' in error_msg:
                            st.error("❌ Login failed - check username/password")
                        else:
                            st.error(f"❌ FTP Error: {error_msg}")
                    except socket.gaierror:
                        st.error("❌ Could not resolve hostname")
                    except socket.timeout:
                        st.error("❌ Connection timed out")
                    except Exception as e:
                        st.error(f"❌ Connection failed: {str(e)}")

elif tool == "🔐 File Permission Checker":
    st.title("🔐 File Permission Checker")
    st.markdown("Convert and understand Unix file permissions")
    
    tab1, tab2, tab3 = st.tabs(["🔢 Numeric to Symbolic", "🔤 Symbolic to Numeric", "📚 Guide"])
    
    with tab1:
        st.markdown("### Numeric to Symbolic Converter")
        numeric = st.text_input("Enter numeric permissions (e.g., 644):", max_chars=3, key="num_input")
        
        if numeric and len(numeric) == 3:
            try:
                def num_to_perm(n):
                    n = int(n)
                    r = 'r' if n & 4 else '-'
                    w = 'w' if n & 2 else '-'
                    x = 'x' if n & 1 else '-'
                    return r + w + x
                
                owner = num_to_perm(numeric[0])
                group = num_to_perm(numeric[1])
                other = num_to_perm(numeric[2])
                
                symbolic = owner + group + other
                
                col1, col2 = st.columns(2)
                with col1:
                    st.markdown("**Symbolic Representation:**")
                    st.code(symbolic, language="bash")
                
                with col2:
                    st.markdown("**Breakdown:**")
                    st.info(f"Owner: {owner}")
                    st.info(f"Group: {group}")
                    st.info(f"Other: {other}")
                
                st.markdown("### 🔍 Security Assessment")
                
                if numeric == "777":
                    st.error("❌ DANGEROUS: Full access for everyone!")
                    st.warning("Never use 777 in production!")
                elif numeric == "666":
                    st.error("❌ INSECURE: Everyone can read/write!")
                elif numeric in ["644", "755"]:
                    st.success("✅ RECOMMENDED: Standard web permissions")
                elif numeric == "600":
                    st.success("✅ SECURE: Owner-only access")
                elif numeric == "700":
                    st.success("✅ SECURE: Owner-only access (with execute)")
                else:
                    st.info("ℹ️ Custom permissions - verify appropriateness")
                
            except (ValueError, IndexError):
                st.error("❌ Invalid format - use numbers 0-7")
    
    with tab2:
        st.markdown("### Symbolic to Numeric Converter")
        st.markdown("Check permissions for each group:")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.markdown("**Owner**")
            owner_r = st.checkbox("Read", key="owner_r")
            owner_w = st.checkbox("Write", key="owner_w")
            owner_x = st.checkbox("Execute", key="owner_x")
        
        with col2:
            st.markdown("**Group**")
            group_r = st.checkbox("Read", key="group_r")
            group_w = st.checkbox("Write", key="group_w")
            group_x = st.checkbox("Execute", key="group_x")
        
        with col3:
            st.markdown("**Other**")
            other_r = st.checkbox("Read", key="other_r")
            other_w = st.checkbox("Write", key="other_w")
            other_x = st.checkbox("Execute", key="other_x")
        
        owner_num = (4 if owner_r else 0) + (2 if owner_w else 0) + (1 if owner_x else 0)
        group_num = (4 if group_r else 0) + (2 if group_w else 0) + (1 if group_x else 0)
        other_num = (4 if other_r else 0) + (2 if other_w else 0) + (1 if other_x else 0)
        
        result = f"{owner_num}{group_num}{other_num}"
        
        st.markdown("### Result")
        st.code(result, language="bash")
        st.code(f"chmod {result} filename", language="bash")
    
    with tab3:
        st.markdown("### 📚 Permission Guide")
        
        st.markdown("**Recommended Permissions:**")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.info("**Files:**")
            st.code("644 - Standard files")
            st.code("600 - Sensitive files (config)")
            st.code("640 - Group readable")
        
        with col2:
            st.info("**Directories:**")
            st.code("755 - Standard folders")
            st.code("750 - Group accessible")
            st.code("700 - Private folders")
        
        st.markdown("---")
        st.markdown("**Permission Values:**")
        
        perm_data = {
            'Number': ['4', '2', '1'],
            'Permission': ['Read (r)', 'Write (w)', 'Execute (x)'],
            'Files': ['View content', 'Modify content', 'Run as program'],
            'Directories': ['List files', 'Add/delete files', 'Access directory']
        }
        
        df = pd.DataFrame(perm_data)
        st.dataframe(df, use_container_width=True)
        
        st.markdown("---")
        st.markdown("**Common Combinations:**")
        
        common = {
            'Permission': ['644', '755', '600', '700', '666', '777'],
            'Description': [
                'Standard file (rw-r--r--)',
                'Standard directory/executable (rwxr-xr-x)',
                'Private file (rw-------)',
                'Private directory (rwx------)',
                '⚠️ World-writable file (rw-rw-rw-)',
                '❌ Dangerous - full access (rwxrwxrwx)'
            ],
            'Use Case': [
                'HTML, images, regular files',
                'Directories, scripts',
                'Config files, passwords',
                'Private directories',
                '⚠️ Rarely appropriate',
                '❌ Never use'
            ]
        }
        
        df_common = pd.DataFrame(common)
        st.dataframe(df_common, use_container_width=True)

# UTILITIES
elif tool == "📚 Help Center":
    st.title("📚 Help Center")
    st.markdown("Quick access to common help topics")
    
    search = st.text_input("🔍 Search:", placeholder="email setup, dns, cpanel...")
    
    if search:
        st.info(f"Searching for: {search}")
    
    st.markdown("### 📂 Popular Categories")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("📧 Email Setup", use_container_width=True):
            st.markdown("""
            **Email Setup Guide:**
            1. Log into cPanel
            2. Go to Email Accounts
            3. Create new account
            4. Configure email client:
               - IMAP: mail.yourdomain.com:993
               - SMTP: mail.yourdomain.com:465
            """)
    
    with col2:
        if st.button("🌐 Domain Setup", use_container_width=True):
            st.markdown("""
            **Domain Setup:**
            1. Point nameservers to hosting
            2. Wait for DNS propagation (24-48 hours)
            3. Add domain in cPanel
            4. Upload files to public_html
            """)
    
    with col3:
        if st.button("🗄️ Database Setup", use_container_width=True):
            st.markdown("""
            **Database Setup:**
            1. Create database in cPanel
            2. Create database user
            3. Add user to database
            4. Note credentials for app config
            """)
    
    st.markdown("---")
    
    col4, col5, col6 = st.columns(3)
    
    with col4:
        if st.button("🔒 SSL Setup", use_container_width=True):
            st.markdown("""
            **SSL Certificate:**
            1. Go to SSL/TLS in cPanel
            2. Click "Manage SSL"
            3. Install Let's Encrypt (AutoSSL)
            4. Force HTTPS in .htaccess
            """)
    
    with col5:
        if st.button("📁 FTP Setup", use_container_width=True):
            st.markdown("""
            **FTP Access:**
            - Host: ftp.yourdomain.com
            - Username: your-cpanel-user
            - Password: your-cpanel-password
            - Port: 21 (or 22 for SFTP)
            """)
    
    with col6:
        if st.button("🔧 Troubleshooting", use_container_width=True):
            st.markdown("""
            **Common Issues:**
            - Check error logs first
            - Verify DNS is correct
            - Check file permissions
            - Clear browser cache
            - Test in incognito mode
            """)

elif tool == "🔑 Password Strength Meter":
    st.title("🔑 Password Strength Meter")
    st.warning("🔒 Checked locally - password never sent anywhere")
    
    password = st.text_input("Enter password to test:", type="password", key="pwd_test")
    
    if password:
        strength, score, feedback, color = check_password_strength(password)
        
        st.markdown(f"### Strength: {strength}")
        st.progress(score / 6)
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Length", len(password))
        with col2:
            has_lower = "✅" if re.search(r'[a-z]', password) else "❌"
            st.metric("Lowercase", has_lower)
        with col3:
            has_upper = "✅" if re.search(r'[A-Z]', password) else "❌"
            st.metric("Uppercase", has_upper)
        with col4:
            has_number = "✅" if re.search(r'\d', password) else "❌"
            st.metric("Numbers", has_number)
        
        if feedback:
            st.markdown("### 💡 Suggestions:")
            for tip in feedback:
                st.info(f"• {tip}")
    
    st.markdown("---")
    st.markdown("### 🎲 Password Generator")
    
    col1, col2 = st.columns(2)
    
    with col1:
        length = st.slider("Password Length:", 8, 32, 16)
    
    with col2:
        include_special = st.checkbox("Include Special Characters", value=True)
    
    if st.button("🎲 Generate Secure Password", type="primary"):
        import string
        if include_special:
            chars = string.ascii_letters + string.digits + string.punctuation
        else:
            chars = string.ascii_letters + string.digits
        
        generated = ''.join(random.choice(chars) for _ in range(length))
        st.code(generated)
        st.success("✅ Copy this password to a secure location")

elif tool == "🌍 Timezone Converter":
    st.title("🌍 Timezone Converter")
    
    if not PYTZ_AVAILABLE:
        st.warning("⚠️ Advanced timezone features require pytz library")
        st.info("Basic conversion available")
    
    from_time = st.time_input("Time:")
    offset_from = st.number_input("From UTC Offset (hours):", value=0, min_value=-12, max_value=14)
    offset_to = st.number_input("To UTC Offset (hours):", value=0, min_value=-12, max_value=14)
    
    if from_time:
        from datetime import timedelta
        
        utc_dt = datetime.combine(datetime.today(), from_time)
        from_dt = utc_dt - timedelta(hours=offset_from)
        to_dt = from_dt + timedelta(hours=offset_to)
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.info(f"**From (UTC{offset_from:+d})**")
            st.code(from_time.strftime('%H:%M:%S'))
        
        with col2:
            st.success(f"**UTC**")
            st.code(from_dt.strftime('%H:%M:%S'))
        
        with col3:
            st.info(f"**To (UTC{offset_to:+d})**")
            st.code(to_dt.strftime('%H:%M:%S'))

elif tool == "📋 Copy-Paste Utilities":
    st.title("📋 Copy-Paste Utilities")
    
    tab1, tab2, tab3 = st.tabs(["🔤 Case Converter", "📝 Line Tools", "🔧 Text Tools"])
    
    with tab1:
        text = st.text_area("Enter text:", height=150, key="case_text")
        
        if text:
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("**UPPERCASE**")
                st.text_area("", value=text.upper(), height=100, key="upper")
                
                st.markdown("**Title Case**")
                st.text_area("", value=text.title(), height=100, key="title")
            
            with col2:
                st.markdown("**lowercase**")
                st.text_area("", value=text.lower(), height=100, key="lower")
                
                st.markdown("**Sentence case**")
                st.text_area("", value=text.capitalize(), height=100, key="sentence")
    
    with tab2:
        lines = st.text_area("Enter lines (one per line):", height=150, key="lines_text")
        
        if lines:
            line_list = [l.strip() for l in lines.split('\n') if l.strip()]
            
            col1, col2 = st.columns(2)
            
            with col1:
                if st.button("Remove Duplicates"):
                    unique = list(dict.fromkeys(line_list))
                    st.text_area("Result:", value='\n'.join(unique), height=150, key="unique")
            
            with col2:
                if st.button("Sort A-Z"):
                    sorted_lines = sorted(line_list)
                    st.text_area("Result:", value='\n'.join(sorted_lines), height=150, key="sorted")
            
            st.info(f"📊 Total: {len(line_list)} lines, Unique: {len(set(line_list))} lines")
    
    with tab3:
        text_tool = st.text_area("Enter text:", height=150, key="text_tools")
        
        if text_tool:
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("Characters", len(text_tool))
                st.metric("Words", len(text_tool.split()))
            
            with col2:
                st.metric("Lines", len(text_tool.split('\n')))
                st.metric("Spaces", text_tool.count(' '))
            
            with col3:
                st.metric("Alphanumeric", sum(c.isalnum() for c in text_tool))
                st.metric("Special Chars", sum(not c.isalnum() and not c.isspace() for c in text_tool))

elif tool == "📸 Screenshot Annotator":
    st.title("📸 Screenshot Annotator")
    st.markdown("Upload screenshots and add notes")
    
    uploaded = st.file_uploader("Upload Screenshot:", type=['png', 'jpg', 'jpeg'])
    
    if uploaded:
        image = Image.open(uploaded)
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.image(image, use_container_width=True)
        
        with col2:
            st.markdown("### Image Info")
            st.info(f"**Size:** {image.size[0]} x {image.size[1]}")
            st.info(f"**Format:** {image.format}")
            st.info(f"**Mode:** {image.mode}")
        
        notes = st.text_area("Add Notes:", height=200, placeholder="Describe what's shown in the screenshot...")
        
        if notes:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            
            col1, col2 = st.columns(2)
            
            with col1:
                if st.button("💾 Save Notes"):
                    st.download_button(
                        "📥 Download Notes",
                        notes,
                        f"screenshot_notes_{timestamp}.txt",
                        "text/plain"
                    )
            
            with col2:
                # Convert image to bytes for download
                buf = io.BytesIO()
                image.save(buf, format='PNG')
                st.download_button(
                    "📥 Download Image",
                    buf.getvalue(),
                    f"screenshot_{timestamp}.png",
                    "image/png"
                )

elif tool == "📝 Session Notes":
    st.title("📝 Session Notes")
    st.markdown("Take notes during support sessions")
    
    st.session_state.session_notes = st.text_area(
        "Session Notes:",
        value=st.session_state.session_notes,
        height=400,
        placeholder="Document your troubleshooting steps, findings, and solutions..."
    )
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        if st.button("💾 Save", use_container_width=True):
            st.success("✅ Notes saved in session")
    
    with col2:
        if st.button("📋 Add Timestamp", use_container_width=True):
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            st.session_state.session_notes += f"\n\n--- {timestamp} ---\n"
            st.rerun()
    
    with col3:
        if st.session_state.session_notes:
            st.download_button(
                "📥 Download",
                st.session_state.session_notes,
                f"support_notes_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
                "text/plain",
                use_container_width=True
            )
    
    with col4:
        if st.button("🗑️ Clear All", use_container_width=True):
            st.session_state.session_notes = ""
            st.rerun()
    
    if st.session_state.session_notes:
        word_count = len(st.session_state.session_notes.split())
        char_count = len(st.session_state.session_notes)
        st.info(f"📊 {word_count} words, {char_count} characters")

elif tool == "🗑️ Clear Cache Instructions":
    st.title("🗑️ Clear Cache Instructions")
    st.markdown("Step-by-step guide to clear browser cache")
    
    browser = st.selectbox("Select Browser:", ["Chrome", "Firefox", "Safari", "Edge", "Opera"])
    
    st.markdown("---")
    
    if browser == "Chrome":
        st.markdown("""
        ### Google Chrome
        
        **Quick Method:**
        1. Press `Ctrl+Shift+Delete` (Windows/Linux) or `Cmd+Shift+Delete` (Mac)
        2. Select "All time" from the time range dropdown
        3. Check "Cached images and files"
        4. Click "Clear data"             
        """)
