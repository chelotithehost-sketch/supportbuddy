import streamlit as st
import requests
import json
from datetime import datetime
import socket
import ssl
import whois
from whois import exceptions
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

# Page Configuration
st.set_page_config(
    page_title="Your Support Buddy",
    page_icon="🔧",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Enhanced Custom CSS for better responsive feel
st.markdown("""
    <style>
    /* Main container styling */
    .main {
        padding: 1rem 2rem;
    }
    
    /* Tool button styling */
    .tool-button {
        padding: 1.5rem;
        border-radius: 12px;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        text-align: center;
        margin: 0.5rem 0;
        cursor: pointer;
        transition: all 0.3s ease;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    
    .tool-button:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 12px rgba(0,0,0,0.15);
    }
    
    /* Card styling */
    .info-card {
        background: white;
        border-radius: 12px;
        padding: 1.5rem;
        box-shadow: 0 2px 8px rgba(0,0,0,0.08);
        margin: 1rem 0;
        border-left: 4px solid #667eea;
    }
    
    /* Result boxes */
    .success-box {
        padding: 1.5rem;
        border-radius: 12px;
        background: linear-gradient(135deg, #d1fae5 0%, #a7f3d0 100%);
        border-left: 6px solid #10b981;
        margin: 1rem 0;
        box-shadow: 0 2px 6px rgba(16,185,129,0.1);
    }
    
    .warning-box {
        padding: 1.5rem;
        border-radius: 12px;
        background: linear-gradient(135deg, #fef3c7 0%, #fde68a 100%);
        border-left: 6px solid #f59e0b;
        margin: 1rem 0;
        box-shadow: 0 2px 6px rgba(245,158,11,0.1);
    }
    
    .error-box {
        padding: 1.5rem;
        border-radius: 12px;
        background: linear-gradient(135deg, #fee2e2 0%, #fecaca 100%);
        border-left: 6px solid #ef4444;
        margin: 1rem 0;
        box-shadow: 0 2px 6px rgba(239,68,68,0.1);
    }
    
    .info-box {
        padding: 1.5rem;
        border-radius: 12px;
        background: linear-gradient(135deg, #dbeafe 0%, #bfdbfe 100%);
        border-left: 6px solid #3b82f6;
        margin: 1rem 0;
        box-shadow: 0 2px 6px rgba(59,130,246,0.1);
    }
    
    /* Button styling */
    .stButton>button {
        border-radius: 8px;
        font-weight: 600;
        transition: all 0.3s ease;
    }
    
    .stButton>button:hover {
        transform: translateY(-1px);
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
    }
    
    /* Metric cards */
    div[data-testid="metric-container"] {
        background: linear-gradient(135deg, #f3f4f6 0%, #e5e7eb 100%);
        border-radius: 12px;
        padding: 1rem;
        box-shadow: 0 2px 6px rgba(0,0,0,0.05);
    }
    
    /* Expander styling */
    .streamlit-expanderHeader {
        background-color: #f9fafb;
        border-radius: 8px;
        font-weight: 600;
    }
    
    /* Input fields */
    .stTextInput>div>div>input,
    .stTextArea>div>div>textarea {
        border-radius: 8px;
        border: 2px solid #e5e7eb;
        transition: border-color 0.3s ease;
    }
    
    .stTextInput>div>div>input:focus,
    .stTextArea>div>div>textarea:focus {
        border-color: #667eea;
        box-shadow: 0 0 0 3px rgba(102,126,234,0.1);
    }
    </style>
""", unsafe_allow_html=True)

# Configure Gemini API
GEMINI_API_KEY = ""
try:
    GEMINI_API_KEY = st.secrets.get("GEMINI_API_KEY", "")
    if GEMINI_API_KEY:
        import google.generativeai as genai
        genai.configure(api_key=GEMINI_API_KEY)
except:
    pass

try:
    import google.generativeai as genai
    from google.api_core import exceptions as google_exceptions
except ImportError:
    google_exceptions = None

# Vision-capable models for ticket analysis
GEMINI_MODELS = ["gemini-2.5-flash", "gemini-2.5-flash-lite", "gemini-2.0-flash", "gemini-2.0-flash-exp", "gemini-1.5-pro", "gemini-1.5-flash"]

# Create persistent session for .ng WHOIS queries
ng_session = requests.Session()
retry = Retry(total=3, backoff_factor=0.5)
adapter = HTTPAdapter(max_retries=retry, pool_connections=10, pool_maxsize=100)
ng_session.mount('https://', adapter)

# Function to parse bulk input for nameserver authority checking
def parse_input(text):
    """Parse input text into domain and nameserver pairs"""
    lines = text.strip().split('\n')
    parsed = []
    
    for line in lines:
        if not line.strip():
            continue
        
        # Split by comma or tab
        parts = [p.strip() for p in line.replace('\t', ',').split(',')]
        
        if len(parts) >= 2:
            domain = parts[0].lower().replace('https://', '').replace('http://', '').replace('/', '')
            nameservers = [ns for ns in parts[1:] if ns]
            
            if domain and nameservers:
                parsed.append({
                    'domain': domain,
                    'nameservers': nameservers
                })
    
    return parsed

# Function to check nameserver authority
def check_nameserver_authority(domain, nameservers):
    """Check if nameservers are authoritative for a domain"""
    try:
        # Query Google DNS API
        url = f"https://dns.google/resolve?name={domain}&type=NS"
        response = requests.get(url, timeout=10)
        dns_data = response.json()
        
        # Check if query was successful
        if dns_data.get('Status') != 0 or 'Answer' not in dns_data:
            return {
                'domain': domain,
                'requested_ns': nameservers,
                'actual_ns': [],
                'is_authoritative': False,
                'status': 'error',
                'message': 'Unable to resolve domain nameservers',
                'suggestions': [
                    'Verify the domain is registered and active',
                    'Check if the domain has been delegated properly',
                    'Ensure DNS propagation is complete (can take 24-48 hours)'
                ]
            }
        
        # Extract actual nameservers
        actual_ns = []
        for record in dns_data.get('Answer', []):
            if record.get('type') == 2:  # NS record
                ns = record.get('data', '').lower().rstrip('.')
                actual_ns.append(ns)
        
        # Normalize requested nameservers
        requested_ns_normalized = [ns.lower().rstrip('.') for ns in nameservers]
        
        # Check if all requested nameservers match
        all_match = all(
            any(actual == req or actual in req or req in actual 
                for actual in actual_ns)
            for req in requested_ns_normalized
        )
        
        some_match = any(
            any(actual == req or actual in req or req in actual 
                for actual in actual_ns)
            for req in requested_ns_normalized
        )
        
        # Determine status and suggestions
        if all_match:
            status = 'success'
            message = '✅ All nameservers are authoritative'
            suggestions = [
                '✓ Domain is properly configured',
                '✓ Nameserver changes can be made at the registrar',
                '✓ Any DNS changes will propagate from these nameservers'
            ]
        elif some_match:
            status = 'partial'
            message = '⚠️ Some nameservers match, but not all'
            missing_ns = [ns for ns in actual_ns 
                         if not any(req == ns or req in ns or ns in req 
                                   for req in requested_ns_normalized)]
            suggestions = [
                '→ Update nameservers at your domain registrar to match exactly',
                '→ Remove old/incorrect nameservers',
                f'→ Add missing nameservers: {", ".join(missing_ns)}' if missing_ns else '',
                '→ Wait 24-48 hours for DNS propagation after making changes'
            ]
            suggestions = [s for s in suggestions if s]
        else:
            status = 'mismatch'
            message = '❌ Requested nameservers are NOT authoritative'
            suggestions = [
                f'→ Current authoritative nameservers: {", ".join(actual_ns)}',
                '→ Update nameservers at your domain registrar (e.g., where you bought the domain)',
                '→ For .co.za domains, update via your registrar\'s control panel',
                '→ After updating, wait 24-48 hours for propagation',
                '→ Verify the nameservers you want to use are correctly configured'
            ]
        
        return {
            'domain': domain,
            'requested_ns': nameservers,
            'actual_ns': actual_ns,
            'is_authoritative': all_match,
            'status': status,
            'message': message,
            'suggestions': suggestions
        }
        
    except requests.exceptions.Timeout:
        return {
            'domain': domain,
            'requested_ns': nameservers,
            'actual_ns': [],
            'is_authoritative': False,
            'status': 'error',
            'message': 'Request timeout - DNS server not responding',
            'suggestions': [
                'Check your internet connection',
                'Try again in a few moments',
                'The DNS server may be experiencing issues'
            ]
        }
    except Exception as e:
        return {
            'domain': domain,
            'requested_ns': nameservers,
            'actual_ns': [],
            'is_authoritative': False,
            'status': 'error',
            'message': f'Error: {str(e)}',
            'suggestions': [
                'Check your internet connection',
                'Verify the domain name is correct',
                'Try again in a few moments'
            ]
        }

# Function to display nameserver check results
def display_ns_result(result):
    """Display a single nameserver check result with appropriate styling"""
    status = result['status']
    
    if status == 'success':
        box_class = 'success-box'
        icon = '✅'
    elif status == 'partial':
        box_class = 'warning-box'
        icon = '⚠️'
    else:
        box_class = 'error-box'
        icon = '❌'
    
    st.markdown(f'<div class="{box_class}">', unsafe_allow_html=True)
    st.markdown(f"### {icon} {result['domain']}")
    st.markdown(f"**{result['message']}**")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**Requested Nameservers:**")
        for ns in result['requested_ns']:
            st.code(ns, language=None)
    
    with col2:
        st.markdown("**Actual Authoritative Nameservers:**")
        if result['actual_ns']:
            for ns in result['actual_ns']:
                st.code(ns, language=None)
        else:
            st.write("*None found*")
    
    st.markdown("**Suggestions:**")
    for suggestion in result['suggestions']:
        st.write(f"• {suggestion}")
    
    st.markdown('</div>', unsafe_allow_html=True)

# Function to convert results to CSV
def convert_results_to_csv(results):
    """Convert results to CSV format"""
    data = []
    for result in results:
        data.append({
            'Domain': result['domain'],
            'Requested Nameservers': '; '.join(result['requested_ns']),
            'Actual Nameservers': '; '.join(result['actual_ns']),
            'Status': result['status'],
            'Message': result['message'],
            'Suggestions': ' | '.join(result['suggestions'])
        })
    
    df = pd.DataFrame(data)
    return df.to_csv(index=False)

# Function to query .ng WHOIS
def query_ng_whois(domain):
    """Query WHOIS information for .ng domains"""
    url = f"https://whois.net.ng/whois/{domain}"
    try:
        response = ng_session.get(url, timeout=10)
        return response.text
    except Exception as e:
        return f"Error: {e}"

# Function to check .ng nameservers
def check_ng_nameservers(domain):
    """Check nameservers for .ng domains using DNS lookup"""
    try:
        # Use Google DNS API for .ng domains
        url = f"https://dns.google/resolve?name={domain}&type=NS"
        response = requests.get(url, timeout=10)
        dns_data = response.json()
        
        if dns_data.get('Status') == 0 and 'Answer' in dns_data:
            nameservers = []
            for record in dns_data.get('Answer', []):
                if record.get('type') == 2:  # NS record
                    ns = record.get('data', '').lower().rstrip('.')
                    nameservers.append(ns)
            return nameservers
        else:
            return None
    except Exception as e:
        return None

# KB Database - HostAfrica Knowledge Base (Comprehensive)
HOSTAFRICA_KB = {
    'web_hosting': [
        {'title': 'Reseller Web Hosting', 'url': 'https://help.hostafrica.com/category/reseller-web-hosting-pricing',
         'keywords': ['reseller', 'hosting', 'web hosting', 'shared hosting']},
        {'title': 'DirectAdmin Web Hosting', 'url': 'https://help.hostafrica.com/article/affordable-and-reliable-shared-directadmin-web-hosting-in-africa',
         'keywords': ['directadmin', 'shared hosting', 'web hosting']},
        {'title': 'Upload Website via FTP', 'url': 'https://help.hostafrica.com/article/how-to-upload-your-website-using-ftp-via-filezilla',
         'keywords': ['ftp', 'upload', 'filezilla', 'website']},
        {'title': 'Troubleshooting Slow Website', 'url': 'https://help.hostafrica.com/article/troubleshooting-a-slow-website',
         'keywords': ['slow', 'performance', 'speed', 'loading']},
        {'title': 'Index of / Error Fix', 'url': 'https://help.hostafrica.com/article/why-do-i-get-an-index-of-when-i-visit-my-site',
         'keywords': ['index of', 'directory listing', 'website error']},
    ],
    'dns_nameservers': [
        {'title': 'DNS and Nameservers', 'url': 'https://help.hostafrica.com/category/dns-and-nameservers',
         'keywords': ['dns', 'nameserver', 'ns', 'propagation']},
        {'title': 'DNS Changes via Client Area', 'url': 'https://help.hostafrica.com/article/dns-changes-via-the-hostafrica-customer-section',
         'keywords': ['dns', 'client area', 'change nameservers']},
        {'title': 'cPanel Zone Editor', 'url': 'https://help.hostafrica.com/article/cpanel-zone-editor-dns',
         'keywords': ['zone editor', 'dns records', 'cpanel dns']},
        {'title': 'Add Google MX Records', 'url': 'https://help.hostafrica.com/article/how-to-add-google-mx-records-via-cpanel',
         'keywords': ['google', 'mx records', 'gmail', 'workspace']},
        {'title': 'Managing DNS in DirectAdmin', 'url': 'https://help.hostafrica.com/article/managing-dns-settings-in-directadmin',
         'keywords': ['directadmin', 'dns', 'zone', 'records']},
    ],
    'cpanel': [
        {'title': 'cPanel Category', 'url': 'https://help.hostafrica.com/category/control-panel-and-emails/cpanel',
         'keywords': ['cpanel', 'control panel', 'login', 'access']},
        {'title': 'cPanel Web Disk', 'url': 'https://help.hostafrica.com/article/how-to-access-cpanel-web-disk',
         'keywords': ['web disk', 'webdav', 'cpanel']},
        {'title': 'PHP Version per Domain', 'url': 'https://help.hostafrica.com/article/how-to-set-php-version-per-domain-in-cpanel',
         'keywords': ['php', 'version', 'domain', 'cpanel']},
        {'title': 'Create Addon Domain', 'url': 'https://help.hostafrica.com/article/how-to-add-addon-domain-in-the-new-domains-feature-in-cpanel',
         'keywords': ['addon', 'domain', 'add domain', 'cpanel']},
        {'title': 'Create Subdomain', 'url': 'https://help.hostafrica.com/article/how-to-create-a-subdomain-in-cpanel',
         'keywords': ['subdomain', 'create', 'cpanel']},
        {'title': 'Park Domain', 'url': 'https://help.hostafrica.com/article/how-to-park-a-domain-in-cpanel',
         'keywords': ['park', 'alias', 'domain', 'cpanel']},
    ],
    'directadmin': [
        {'title': 'DirectAdmin Category', 'url': 'https://help.hostafrica.com/category/control-panel-and-emails/directadmin',
         'keywords': ['directadmin', 'control panel', 'da']},
        {'title': 'Email Forwarding DirectAdmin', 'url': 'https://help.hostafrica.com/article/how-to-set-email-forwarding-in-direct-admin',
         'keywords': ['email forward', 'forwarding', 'directadmin']},
        {'title': 'Unban IP DirectAdmin', 'url': 'https://help.hostafrica.com/article/how-to-unban-ip-address-in-direct-admin',
         'keywords': ['unban', 'ip block', 'directadmin']},
        {'title': 'SSL DirectAdmin', 'url': 'https://help.hostafrica.com/article/how-to-install-ssl-certificate-in-direct-admin',
         'keywords': ['ssl', 'certificate', 'directadmin']},
        {'title': 'Site Redirect DirectAdmin', 'url': 'https://help.hostafrica.com/article/how-to-setup-a-site-redirect-in-direct-admin',
         'keywords': ['redirect', '301', 'directadmin']},
        {'title': 'Auto SSL DirectAdmin', 'url': 'https://help.hostafrica.com/article/how-to-install-auto-ssl-from-the-direct-admin-panel',
         'keywords': ['auto ssl', 'let\'s encrypt', 'directadmin']},
    ],
    'email': [
        {'title': 'Email Category', 'url': 'https://help.hostafrica.com/category/control-panel-and-emails/emails',
         'keywords': ['email', 'mail', 'smtp', 'imap', 'pop3']},
        {'title': 'Troubleshooting Email', 'url': 'https://help.hostafrica.com/category/control-panel-and-emails/troubleshooting-email',
         'keywords': ['email not working', 'email issues', 'troubleshoot']},
        {'title': 'Email on iPhone/iOS', 'url': 'https://help.hostafrica.com/article/how-to-set-up-email-on-an-iphone-using-imap-and-ssl',
         'keywords': ['iphone', 'ios', 'mobile', 'email setup']},
        {'title': 'Email in Gmail App', 'url': 'https://help.hostafrica.com/article/adding-an-email-to-gmailnot-google-workspace',
         'keywords': ['gmail', 'android', 'email app']},
        {'title': 'Change iPhone Email Signature', 'url': 'https://help.hostafrica.com/article/how-to-change-the-sent-from-my-iphone-email-signature-on-ios',
         'keywords': ['signature', 'iphone', 'email']},
    ],
    'domains': [
        {'title': 'Domains Category', 'url': 'https://help.hostafrica.com/category/domains',
         'keywords': ['domain', 'registration', 'transfer', 'renewal']},
        {'title': 'Domains Management', 'url': 'https://help.hostafrica.com/category/domains-management',
         'keywords': ['manage domain', 'domain settings']},
        {'title': 'Domain Registration', 'url': 'https://help.hostafrica.com/article/how-do-i-register-my-domain-name',
         'keywords': ['register', 'new domain', 'buy domain']},
        {'title': 'Domain Transfer', 'url': 'https://help.hostafrica.com/article/how-to-transfer-domains-to-us',
         'keywords': ['transfer', 'epp', 'auth code']},
        {'title': 'Domain Redemption', 'url': 'https://help.hostafrica.com/article/domain-redemption',
         'keywords': ['redemption', 'expired', 'grace period']},
        {'title': 'Enable Auto-Renew', 'url': 'https://help.hostafrica.com/article/how-to-enable-auto-renew-on-a-domain-name',
         'keywords': ['auto renew', 'renewal', 'automatic']},
        {'title': 'Update WHOIS Info', 'url': 'https://help.hostafrica.com/article/updating-the-contact-whois-information-on-your-domain',
         'keywords': ['whois', 'contact', 'registrant']},
    ],
    'ssl': [
        {'title': 'SSL Certificates', 'url': 'https://help.hostafrica.com/category/ssl-certificates',
         'keywords': ['ssl', 'https', 'certificate', 'secure', 'tls']},
        {'title': 'Generate SSL Certificate', 'url': 'https://help.hostafrica.com/article/how-to-generate-and-retrieve-your-ssl-certificate-from-the-hostafrica-client-area',
         'keywords': ['ssl', 'generate', 'purchase']},
        {'title': 'AutoSSL in cPanel', 'url': 'https://help.hostafrica.com/article/how-to-run-autossl-on-your-domains-to-install-an-ssl-via-cpanel',
         'keywords': ['autossl', 'let\'s encrypt', 'free ssl', 'cpanel']},
    ]
}

def search_kb(query):
    """Search knowledge base for relevant articles"""
    query = query.lower()
    results = []
    
    for category, articles in HOSTAFRICA_KB.items():
        for article in articles:
            # Check if query matches title or keywords
            if query in article['title'].lower():
                results.append({**article, 'category': category, 'relevance': 2})
            elif any(query in keyword for keyword in article['keywords']):
                results.append({**article, 'category': category, 'relevance': 1})
    
    # Sort by relevance
    results.sort(key=lambda x: x['relevance'], reverse=True)
    return results[:10]

# Initialize session state for AI chat
if 'chat_history' not in st.session_state:
    st.session_state.chat_history = []

# Sidebar Navigation
st.sidebar.title("🔧 Support Buddy")
st.sidebar.markdown("---")

tool = st.sidebar.radio(
    "Select Tool:",
    ["🏠 Home", "🔐 PIN Checker", "🔓 IP Unban", "🔍 DNS Lookup", "🌍 WHOIS Lookup", "🗂️ DNS Analyzer", "🔒 SSL Checker", "📚 Help Center", "🧹 Flush DNS Cache", "💬 AI Support Chat", "🔍 IP Address Lookup", "🔄 Bulk NS Updater", "📂 cPanel Account List"],
    label_visibility="collapsed"
)

st.sidebar.markdown("---")
st.sidebar.markdown("### Quick Links")
st.sidebar.link_button("📚 Help Center", "https://help.hostafrica.com", use_container_width=True)
st.sidebar.link_button("🧹 Flush Google DNS", "https://dns.google/cache", use_container_width=True)
st.sidebar.markdown("---")
st.sidebar.caption("🔧 HostAfrica Support Tools v2.0")

# Main Content Area
if tool == "🏠 Home":
    st.title("🔧 Your Support Buddy")
    st.markdown("### Welcome to HostAfrica Support Tools")
    
    st.markdown('<div class="info-box">', unsafe_allow_html=True)
    st.markdown("""
**Quick access to essential support tools:**
- 🏠 Home  
- 🔐 PIN Checker  
- 🔓 IP Unban  
- 🔍 DNS Lookup  
- 🌍 WHOIS Lookup (.ng domains supported)  
- 🗂️ DNS Analyzer  
- 🔒 SSL Checker  
- 📚 Help Center  
- 🧹 Flush DNS Cache  
- 💬 AI Support Chat  
- 🔍 IP Address Lookup  
- 🔄 Bulk NS Updater  
- 📂 cPanel Account List  
- 📋 Support Ticket Tools  
- 🤖 AI-Powered Ticket Analysis  
""")
st.markdown('</div>', unsafe_allow_html=True)
    
    # Add dedicated buttons for ticket tools
    st.markdown("### 🎫 Ticket Management Tools")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("📋 Support Ticket Checklist", use_container_width=True, type="primary"):
            st.session_state.show_checklist = True
            st.session_state.show_analysis = False
    
    with col2:
        if st.button("🤖 AI Ticket Analysis", use_container_width=True, type="primary"):
            st.session_state.show_analysis = True
            st.session_state.show_checklist = False
    
    # Display Support Ticket Checklist if toggled
    if st.session_state.get('show_checklist', False):
        st.markdown("---")
        st.markdown("## 📋 Support Ticket Checklist")
        
        st.markdown('<div class="info-card">', unsafe_allow_html=True)
        st.markdown("""
        Use this checklist to ensure you've gathered all necessary information before responding to a ticket.
        """)
        st.markdown('</div>', unsafe_allow_html=True)
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("#### 📝 Initial Assessment")
            check1 = st.checkbox("Customer's main issue identified")
            check2 = st.checkbox("Ticket category verified")
            check3 = st.checkbox("Priority level assessed")
            check4 = st.checkbox("Customer account verified")
            
            st.markdown("#### 🔍 Information Gathering")
            check5 = st.checkbox("Domain name(s) collected")
            check6 = st.checkbox("Error messages documented")
            check7 = st.checkbox("Steps to reproduce noted")
            check8 = st.checkbox("Screenshots/logs reviewed")
        
        with col2:
            st.markdown("#### 🛠️ Technical Checks")
            check9 = st.checkbox("DNS records verified")
            check10 = st.checkbox("Hosting status checked")
            check11 = st.checkbox("SSL certificate validated")
            check12 = st.checkbox("Email configuration reviewed")
            
            st.markdown("#### ✅ Before Responding")
            check13 = st.checkbox("Solution tested/verified")
            check14 = st.checkbox("KB articles referenced")
            check15 = st.checkbox("Follow-up plan created")
            check16 = st.checkbox("Response tone is professional")
        
        all_checks = [check1, check2, check3, check4, check5, check6, check7, check8,
                     check9, check10, check11, check12, check13, check14, check15, check16]
        
        progress = sum(all_checks) / len(all_checks)
        
        st.markdown("---")
        st.markdown(f"### Progress: {int(progress * 100)}%")
        st.progress(progress)
        
        if progress == 1.0:
            st.success("✅ All checks complete! You're ready to respond to the ticket.")
        elif progress >= 0.5:
            st.info(f"📊 {sum(all_checks)}/{len(all_checks)} checks complete. Keep going!")
        else:
            st.warning(f"⚠️ {sum(all_checks)}/{len(all_checks)} checks complete. More information needed.")
        
        if st.button("🔄 Reset Checklist"):
            st.session_state.show_checklist = False
            st.rerun()
    
    # Display AI Ticket Analysis if toggled
    elif st.session_state.get('show_analysis', False):
        st.markdown("---")
        st.markdown("## 🤖 AI Ticket Analysis")
        
        if not GEMINI_API_KEY:
            st.error("⚠️ Gemini API key not configured. Please add your API key to secrets.")
            st.info("💡 Add 'GEMINI_API_KEY' to your Streamlit secrets to enable this feature.")
        else:
            st.markdown('<div class="info-card">', unsafe_allow_html=True)
            st.markdown("""
            Upload a screenshot of a support ticket for AI-powered analysis and suggested responses.
            """)
            st.markdown('</div>', unsafe_allow_html=True)
            
            # Model selection
            selected_model = st.selectbox(
                "Select AI Model:",
                GEMINI_MODELS,
                help="Choose the Gemini model for analysis"
            )
            
            # Image upload
            uploaded_file = st.file_uploader(
                "Upload Ticket Screenshot",
                type=['png', 'jpg', 'jpeg'],
                help="Upload a clear screenshot of the support ticket"
            )
            
            if uploaded_file:
                # Display uploaded image
                image = Image.open(uploaded_file)
                st.image(image, caption="Uploaded Ticket", use_column_width=True)
                
                # Analysis button
                if st.button("🔍 Analyze Ticket", type="primary"):
                    with st.spinner("🤖 AI is analyzing the ticket..."):
                        try:
                            # Configure Gemini
                            model = genai.GenerativeModel(selected_model)
                            
                            # Prepare the prompt
                            prompt = """
                            You are a HostAfrica technical support expert. Analyze this support ticket screenshot and provide:
                            
                            1. **Ticket Summary**: Brief overview of the customer's issue
                            2. **Issue Category**: Classify the issue (e.g., DNS, Email, Hosting, SSL, Domain)
                            3. **Priority Level**: Suggest priority (Low/Medium/High/Urgent)
                            4. **Key Information**: Extract important details (domain names, error messages, etc.)
                            5. **Technical Analysis**: Identify potential causes
                            6. **Suggested Solution**: Step-by-step resolution plan
                            7. **KB Articles**: Recommend relevant HostAfrica help articles
                            8. **Draft Response**: Professional response template for the customer
                            
                            Be thorough, technical, and customer-focused in your analysis.
                            """
                            
                            # Generate analysis
                            response = model.generate_content([prompt, image])
                            
                            st.markdown('<div class="success-box">', unsafe_allow_html=True)
                            st.markdown("### 🤖 AI Analysis Results")
                            st.markdown(response.text)
                            st.markdown('</div>', unsafe_allow_html=True)
                            
                            # Option to search KB based on analysis
                            st.markdown("---")
                            if st.button("🔍 Search KB for Related Articles"):
                                # Extract keywords from the analysis
                                keywords = ['dns', 'email', 'ssl', 'cpanel']  # You can make this smarter
                                st.info("Searching knowledge base...")
                                
                        except Exception as e:
                            st.error(f"❌ Error analyzing ticket: {str(e)}")
                            st.info("💡 Make sure your API key is valid and the model is accessible.")
            
            if st.button("🔙 Back to Home"):
                st.session_state.show_analysis = False
                st.rerun()

# TOOLS
if tool == "🔐 PIN Checker":
    st.header("🔐 PIN Checker")
    col1, col2 = st.columns([3, 1])
    with col1:
        st.info("Verify client PIN")
    with col2:
        st.link_button("Open", "https://my.hostafrica.com/admin/admin_tool/client-pin", use_container_width=True)

elif tool == "🔓 IP Unban":
    st.header("🔓 IP Unban")
    col1, col2 = st.columns([3, 1])
    with col1:
        st.info("Remove IP blocks")
    with col2:
        st.link_button("Open", "https://my.hostafrica.com/admin/custom/scripts/unban/", use_container_width=True)

elif tool == "🗂️ DNS Analyzer":
    st.header("🗂️ DNS Analyzer")
    st.markdown("Comprehensive DNS analysis with all record types")
    
    domain_dns = st.text_input("Enter domain:", placeholder="example.com")
    
    if st.button("🔍 Analyze DNS", use_container_width=True):
        if domain_dns:
            domain_dns = domain_dns.strip().lower()
            
            with st.spinner("Analyzing DNS..."):
                issues, warnings, success_checks = [], [], []
                
                # A Records
                st.subheader("🌐 A Records")
                try:
                    a_res = requests.get(f"https://dns.google/resolve?name={domain_dns}&type=A", timeout=5).json()
                    if a_res.get('Answer'):
                        st.success(f"✅ Found {len(a_res['Answer'])} A record(s)")
                        for r in a_res['Answer']:
                            st.code(f"A: {r['data']} (TTL: {r.get('TTL', 'N/A')}s)")
                        success_checks.append("A record found")
                    else:
                        issues.append("Missing A record")
                        st.error("❌ No A records")
                except Exception as e:
                    st.error(f"Error: {str(e)}")

                # MX Records
                st.subheader("📧 MX Records")
                try:
                    mx_res = requests.get(f"https://dns.google/resolve?name={domain_dns}&type=MX", timeout=5).json()
                    if mx_res.get('Answer'):
                        st.success(f"✅ Found {len(mx_res['Answer'])} mail server(s)")
                        mx_sorted = sorted(mx_res['Answer'], key=lambda x: int(x['data'].split()[0]))
                        for r in mx_sorted:
                            parts = r['data'].split()
                            st.code(f"MX: Priority {parts[0]} → {parts[1].rstrip('.')}")
                        success_checks.append("MX configured")
                    else:
                        issues.append("No MX records")
                        st.error("❌ No MX records")
                except:
                    pass

                # TXT Records
                st.subheader("📝 TXT Records (SPF/DKIM/DMARC)")
                try:
                    txt_res = requests.get(f"https://dns.google/resolve?name={domain_dns}&type=TXT", timeout=5).json()
                    if txt_res.get('Answer'):
                        found_spf = False
                        for r in txt_res['Answer']:
                            val = r['data'].strip('"')
                            if val.startswith('v=spf1'):
                                st.success("🛡️ SPF Found")
                                st.code(f"SPF: {val}")
                                found_spf = True
                            elif val.startswith('v=DMARC'):
                                st.success("🛡️ DMARC Found")
                                st.code(f"DMARC: {val}")
                            else:
                                st.code(f"TXT: {val[:100]}...")
                        
                        if found_spf:
                            success_checks.append("SPF found")
                        else:
                            warnings.append("No SPF record")
                    else:
                        warnings.append("No TXT records")
                except:
                    pass

                # Nameservers
                st.subheader("🖥️ Nameservers")
                try:
                    ns_res = requests.get(f"https://dns.google/resolve?name={domain_dns}&type=NS", timeout=5).json()
                    if ns_res.get('Answer'):
                        st.success(f"✅ Found {len(ns_res['Answer'])} nameserver(s)")
                        for r in ns_res['Answer']:
                            ns = r['data'].rstrip('.')
                            st.code(f"NS: {ns}")
                            if 'host-ww.net' in ns:
                                st.caption("✅ HostAfrica NS")
                        success_checks.append("NS configured")
                    else:
                        issues.append("No nameservers")
                except:
                    pass

                # Summary
                st.divider()
                st.subheader("📊 Summary")
                if not issues and not warnings:
                    st.success("🎉 All DNS checks passed!")
                else:
                    col_a, col_b = st.columns(2)
                    with col_a:
                        for i in issues: st.error(f"• {i}")
                        for w in warnings: st.warning(f"• {w}")
                    with col_b:
                        for s in success_checks: st.success(f"• {s}")

elif tool == "📂 cPanel Account List":
    st.header("📂 cPanel Account List")
    st.markdown("View all cPanel hosting accounts and their details")
    col1, col2 = st.columns([3, 1])
    with col1:
        st.info("Access the complete list of cPanel accounts")
    with col2:
        st.link_button("📂 Open List", "https://my.hostafrica.com/admin/custom/scripts/custom_tests/listaccounts.php", use_container_width=True)

elif tool == "🔍 DNS Lookup":
    st.title("🔍 DNS Lookup Tool")
    st.markdown("Check DNS records for any domain, including .co.ng domains")
    
    # Domain input
    domain_input = st.text_input(
        "Enter domain name:",
        placeholder="example.com or example.co.ng",
        help="Enter a domain to look up its DNS records"
    )
    
    # Record type selection
    record_types = st.multiselect(
        "Select record types to query:",
        ["A", "AAAA", "MX", "NS", "TXT", "CNAME", "SOA"],
        default=["A", "NS", "MX"],
        help="Choose which DNS record types to retrieve"
    )
    
    if st.button("🔍 Lookup DNS", type="primary"):
        if domain_input:
            domain = domain_input.strip().lower().replace('https://', '').replace('http://', '').replace('/', '')
            
            # Check if it's a .ng domain
            is_ng_domain = domain.endswith('.ng')
            
            if is_ng_domain:
                st.info("🇳🇬 Detected .ng domain - using specialized lookup")
            
            st.markdown("---")
            
            # Display results for each record type
            for record_type in record_types:
                with st.expander(f"📋 {record_type} Records", expanded=True):
                    try:
                        url = f"https://dns.google/resolve?name={domain}&type={record_type}"
                        response = requests.get(url, timeout=10)
                        data = response.json()
                        
                        if data.get('Status') == 0 and 'Answer' in data:
                            st.markdown(f'<div class="success-box">', unsafe_allow_html=True)
                            st.markdown(f"**✅ Found {len(data['Answer'])} {record_type} record(s)**")
                            
                            for record in data['Answer']:
                                record_data = record.get('data', 'N/A')
                                ttl = record.get('TTL', 'N/A')
                                st.code(f"{record_data} (TTL: {ttl}s)")
                            
                            st.markdown('</div>', unsafe_allow_html=True)
                        else:
                            st.warning(f"⚠️ No {record_type} records found")
                            
                    except Exception as e:
                        st.error(f"❌ Error querying {record_type} records: {str(e)}")
            
            # Special handling for .ng domains - show nameservers
            if is_ng_domain:
                st.markdown("---")
                st.markdown("### 🇳🇬 .ng Domain Nameserver Information")
                
                with st.spinner("Fetching .ng nameservers..."):
                    ng_ns = check_ng_nameservers(domain)
                    
                    if ng_ns:
                        st.markdown('<div class="success-box">', unsafe_allow_html=True)
                        st.markdown(f"**✅ Found {len(ng_ns)} authoritative nameserver(s)**")
                        for ns in ng_ns:
                            st.code(ns)
                        st.markdown('</div>', unsafe_allow_html=True)
                    else:
                        st.warning("⚠️ Could not retrieve nameserver information")
        else:
            st.warning("⚠️ Please enter a domain name")

elif tool == "🔄 Bulk NS Updater":
    st.header("🔄 Bulk Nameserver Updater")
    st.markdown("Update nameservers for multiple domains at once")
    col1, col2 = st.columns([3, 1])
    with col1:
        st.info("Use this tool to bulk update nameservers in WHMCS")
    with col2:
        st.link_button("🔄 Open Updater", "https://my.hostafrica.com/admin/addonmodules.php?module=nameserv_changer", use_container_width=True)						

elif tool == "🌍 WHOIS Lookup":
    st.title("🌍 WHOIS Information Lookup")
    st.markdown("Get WHOIS registration details for any domain (including .ng)")
    
    whois_domain = st.text_input(
        "Enter domain name:",
        placeholder="example.com or example.ng",
        help="Enter a domain to look up its WHOIS information"
    )
    
    if st.button("🔍 Lookup WHOIS", type="primary"):
        if whois_domain:
            domain = whois_domain.strip().lower().replace('https://', '').replace('http://', '').replace('/', '')
            
            # Check if it's a .ng domain
            is_ng_domain = domain.endswith('.ng')
            
            if is_ng_domain:
                st.info("🇳🇬 Using specialized .ng WHOIS lookup")
                
                with st.spinner("Querying .ng WHOIS database..."):
                    whois_data = query_ng_whois(domain)
                    
                    st.markdown('<div class="info-box">', unsafe_allow_html=True)
                    st.markdown("### 🇳🇬 .ng WHOIS Information")
                    st.code(whois_data, language=None)
                    st.markdown('</div>', unsafe_allow_html=True)
            else:
                # Standard WHOIS lookup
                with st.spinner(f"Looking up WHOIS for {domain}..."):
                    try:
                        w = whois.whois(domain)
                        
                        st.markdown('<div class="success-box">', unsafe_allow_html=True)
                        st.markdown("### ✅ WHOIS Information Retrieved")
                        
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            st.markdown("**Registration Details:**")
                            st.write(f"**Domain:** {w.domain_name if hasattr(w, 'domain_name') else 'N/A'}")
                            st.write(f"**Registrar:** {w.registrar if hasattr(w, 'registrar') else 'N/A'}")
                            st.write(f"**Created:** {w.creation_date if hasattr(w, 'creation_date') else 'N/A'}")
                            st.write(f"**Expires:** {w.expiration_date if hasattr(w, 'expiration_date') else 'N/A'}")
                        
                        with col2:
                            st.markdown("### Important Dates")
                            
                            # Creation date
                            if w.creation_date:
                                created = w.creation_date[0] if isinstance(w.creation_date, list) else w.creation_date
                                st.write(f"**Created:** {str(created).split()[0]}")
                            
                            # Updated date
                            if w.updated_date:
                                updated = w.updated_date[0] if isinstance(w.updated_date, list) else w.updated_date
                                st.write(f"**Last Updated:** {str(updated).split()[0]}")
                            
                            # Expiration date
                            if w.expiration_date:
                                exp = w.expiration_date[0] if isinstance(w.expiration_date, list) else w.expiration_date
                                st.write(f"**Expires:** {str(exp).split()[0]}")
                                
                                # Calculate days remaining
                                try:
                                    days_left = (exp - datetime.now().replace(microsecond=0)).days
                                    
                                    if days_left < 0:
                                        st.error(f"❌ **EXPIRED {abs(days_left)} days ago!**")
                                        issues.append(f"Domain expired {abs(days_left)} days ago")
                                    elif days_left < 30:
                                        st.error(f"⚠️ **{days_left} days remaining - URGENT!**")
                                        issues.append(f"Domain expires in {days_left} days")
                                    elif days_left < 90:
                                        st.warning(f"⚠️ **{days_left} days remaining**")
                                        warnings.append(f"Domain expires in {days_left} days")
                                    else:
                                        st.success(f"✅ **{days_left} days remaining**")
                                        success_checks.append("Domain expiration: Good")
                                except:
                                    pass
                        
                        # Nameservers
                        if w.name_servers:
                            st.markdown("### WHOIS Nameservers")
                            ns_list = w.name_servers if isinstance(w.name_servers, list) else [w.name_servers]
                            
                            for ns in ns_list[:5]:
                                ns_clean = str(ns).lower().rstrip('.')
                                st.code(f"• {ns_clean}")
                                
                                if 'host-ww.net' in ns_clean:
                                    st.caption("✅ HostAfrica nameserver")
                        
                        # Full WHOIS data
                        with st.expander("📄 View Full Raw WHOIS Data"):
                            st.json(str(w))
                        
                        # Summary
                        st.divider()
                        st.subheader("📊 WHOIS Health Summary")
                        
                        if not issues and not warnings:
                            st.success("🎉 **Domain is in good standing!** No issues detected.")
                        else:
                            if issues:
                                st.markdown("**❌ Critical Issues:**")
                                for issue in issues:
                                    st.error(f"• {issue}")
                            
                            if warnings:
                                st.markdown("**⚠️ Warnings:**")
                                for warning in warnings:
                                    st.warning(f"• {warning}")
                            
                            if success_checks:
                                st.markdown("**✅ Passed Checks:**")
                                for check in success_checks:
                                    st.success(f"• {check}")
                        
                    else:
                        st.error("❌ Could not retrieve WHOIS information")
                        st.info(f"Try manual lookup at: https://who.is/whois/{domain}")
                        
                except Exception as e:
                    st.error(f"❌ WHOIS lookup failed: {type(e).__name__}")
                    st.warning("Some domains (especially ccTLDs) may not return complete WHOIS data via automated tools.")
                    st.info(f"**Try manual lookup:**\n- https://who.is/whois/{domain}\n- https://lookup.icann.org/en/lookup?name={domain}")
        else:
            st.warning("⚠️ Please enter a domain name")

elif tool == "🔍 IP Address Lookup":
    st.header("🔍 IP Address Lookup")
    st.markdown("Get detailed geolocation and ISP information for any IP address")
    
    ip = st.text_input("Enter IP address:", placeholder="8.8.8.8", key="ip_input")
    
    if st.button("🔍 Lookup IP", use_container_width=True):
        if ip:
            # Validate IP format
            ip_pattern = r'^(\d{1,3}\.){3}\d{1,3}$'
            if not re.match(ip_pattern, ip):
                st.error("❌ Invalid IP address format")
            else:
                with st.spinner(f"Looking up {ip}..."):
                    try:
                        # Try primary API
                        geo_data = None
                        try:
                            response = requests.get(f"https://ipapi.co/{ip}/json/", timeout=5)
                            if response.status_code == 200:
                                geo_data = response.json()
                        except:
                            pass
                        
                        # Fallback API
                        if not geo_data or geo_data.get('error'):
                            response = requests.get(f"http://ip-api.com/json/{ip}", timeout=5)
                            if response.status_code == 200:
                                fallback = response.json()
                                if fallback.get('status') == 'success':
                                    geo_data = {
                                        'ip': ip,
                                        'city': fallback.get('city'),
                                        'region': fallback.get('regionName'),
                                        'country_name': fallback.get('country'),
                                        'postal': fallback.get('zip'),
                                        'latitude': fallback.get('lat'),
                                        'longitude': fallback.get('lon'),
                                        'org': fallback.get('isp'),
                                        'timezone': fallback.get('timezone'),
                                        'asn': fallback.get('as')
                                    }
                        
                        if geo_data and not geo_data.get('error'):
                            st.success(f"✅ Information found for {ip}")
                            
                            col1, col2, col3 = st.columns(3)
                            
                            with col1:
                                st.metric("🌐 IP Address", ip)
                                st.metric("🏙️ City", geo_data.get('city', 'N/A'))
                                st.metric("📮 Postal Code", geo_data.get('postal', 'N/A'))
                            
                            with col2:
                                st.metric("🗺️ Region", geo_data.get('region', 'N/A'))
                                st.metric("🌍 Country", geo_data.get('country_name', 'N/A'))
                                st.metric("🕐 Timezone", geo_data.get('timezone', 'N/A'))
                            
                            with col3:
                                st.metric("📡 ISP/Organization", geo_data.get('org', 'N/A')[:25])
                                if geo_data.get('latitude') and geo_data.get('longitude'):
                                    st.metric("📍 Coordinates", f"{geo_data['latitude']:.4f}, {geo_data['longitude']:.4f}")
                                if geo_data.get('asn'):
                                    st.metric("🔢 ASN", geo_data.get('asn', 'N/A'))
                            
                            # Map link
                            if geo_data.get('latitude') and geo_data.get('longitude'):
                                map_url = f"https://www.google.com/maps?q={geo_data['latitude']},{geo_data['longitude']}"
                                st.markdown(f"🗺️ [View on Google Maps]({map_url})")
                            
                            # Full details
                            with st.expander("🔍 View Full IP Details"):
                                st.json(geo_data)
                        else:
                            st.error("❌ Could not retrieve information for this IP address")
                            st.info("The IP might be private, invalid, or the lookup service is unavailable")
                    except Exception as e:
                        st.error(f"❌ Error: {str(e)}")
        else:
            st.warning("⚠️ Please enter an IP address")


elif tool == "🔒 SSL Checker":
    st.header("🔒 Comprehensive SSL Certificate Checker")
    st.markdown("Verify SSL certificate validity, expiration, and check for mixed content issues")
    
    domain_ssl = st.text_input("Enter domain (without https://):", placeholder="example.com", key="ssl_domain")
    
    if st.button("🔍 Check SSL Certificate", use_container_width=True):
        if domain_ssl:
            domain_ssl = domain_ssl.replace('https://', '').replace('http://', '').replace('www.', '').split('/')[0].strip()
            
            with st.spinner(f"Analyzing SSL certificate for {domain_ssl}..."):
                try:
                    # SSL Certificate Check
                    context = ssl.create_default_context()
                    with socket.create_connection((domain_ssl, 443), timeout=10) as sock:
                        with context.wrap_socket(sock, server_hostname=domain_ssl) as secure_sock:
                            cert = secure_sock.getpeercert()
                            
                            st.success(f"✅ SSL Certificate found and valid for {domain_ssl}")
                            
                            col1, col2 = st.columns(2)
                            
                            with col1:
                                st.subheader("📋 Certificate Details")
                                
                                subject = dict(x[0] for x in cert['subject'])
                                st.write("**Issued To:**", subject.get('commonName', 'N/A'))
                                
                                issuer = dict(x[0] for x in cert['issuer'])
                                st.write("**Issued By:**", issuer.get('commonName', 'N/A'))
                                st.write("**Organization:**", issuer.get('organizationName', 'N/A'))
                            
                            with col2:
                                st.subheader("📅 Validity Period")
                                
                                not_before = cert.get('notBefore')
                                not_after = cert.get('notAfter')
                                
                                st.write("**Valid From:**", not_before)
                                st.write("**Valid Until:**", not_after)
                                
                                if not_after:
                                    try:
                                        expiry_date = datetime.strptime(not_after, '%b %d %H:%M:%S %Y %Z')
                                        days_remaining = (expiry_date - datetime.now()).days
                                        
                                        if days_remaining > 30:
                                            st.success(f"✅ **{days_remaining} days** remaining")
                                        elif days_remaining > 0:
                                            st.warning(f"⚠️ **{days_remaining} days** remaining - Renew soon!")
                                        else:
                                            st.error(f"❌ Certificate expired {abs(days_remaining)} days ago")
                                    except:
                                        pass
                            
                            # Subject Alternative Names
                            if 'subjectAltName' in cert:
                                st.subheader("🌐 Subject Alternative Names (Covered Domains)")
                                sans = [san[1] for san in cert['subjectAltName']]
                                
                                for san in sans[:10]:
                                    st.code(san)
                                
                                if len(sans) > 10:
                                    st.info(f"...and {len(sans) - 10} more domain(s)")
                            
                            # Mixed Content Check
                            st.subheader("🔍 Mixed Content Check")
                            with st.spinner("Checking for mixed content issues..."):
                                try:
                                    # Fetch the homepage
                                    response = requests.get(f"https://{domain_ssl}", timeout=10, verify=True)
                                    content = response.text
                                    
                                    # Check for HTTP resources
                                    http_resources = re.findall(r'http://[^"\'\s<>]+', content)
                                    
                                    if http_resources:
                                        st.warning(f"⚠️ **Found {len(http_resources)} potential mixed content issue(s)**")
                                        st.caption("Mixed content occurs when HTTPS pages load HTTP resources (images, scripts, etc.)")
                                        
                                        # Show first few examples
                                        st.markdown("**Examples:**")
                                        for resource in http_resources[:5]:
                                            st.code(resource)
                                        
                                        if len(http_resources) > 5:
                                            st.info(f"...and {len(http_resources) - 5} more HTTP resources")
                                        
                                        st.markdown("""
                                        **How to fix:**
                                        1. Change all `http://` to `https://` in your HTML/CSS
                                        2. Use protocol-relative URLs: `//example.com/image.jpg`
                                        3. Update your CMS/theme settings to use HTTPS
                                        """)
                                    else:
                                        st.success("✅ No mixed content issues detected!")
                                        st.caption("All resources are loaded securely via HTTPS")
                                except Exception as e:
                                    st.warning(f"⚠️ Could not check for mixed content: {str(e)}")
                            
                            # Certificate summary
                            with st.expander("🔍 View Complete Certificate Summary"):
                                summary = {
                                    'Common Name': subject.get('commonName', 'N/A'),
                                    'Issuer': issuer.get('commonName', 'N/A'),
                                    'Issuer Organization': issuer.get('organizationName', 'N/A'),
                                    'Valid From': not_before,
                                    'Valid Until': not_after,
                                    'Serial Number': cert.get('serialNumber', 'N/A'),
                                    'Version': cert.get('version', 'N/A'),
                                    'Total SANs': len(sans) if 'subjectAltName' in cert else 0
                                }
                                
                                for key, value in summary.items():
                                    st.text(f"{key}: {value}")
                                
                                st.divider()
                                
                                with st.expander("📄 Show Technical/Raw Certificate Data"):
                                    st.json(cert)
                        
                except socket.gaierror:
                    st.error(f"❌ Could not resolve domain: {domain_ssl}")
                    st.info("💡 Make sure the domain name is correct and accessible")
                    
                except socket.timeout:
                    st.error(f"⏱️ Connection timeout for {domain_ssl}")
                    st.info("💡 The server might be slow or blocking connections")
                    
                except ssl.SSLError as ssl_err:
                    st.error(f"❌ SSL Error: {str(ssl_err)}")
                    st.warning("""
                    **Common SSL Issues:**
                    - Certificate has expired
                    - Certificate is self-signed
                    - Certificate name doesn't match domain
                    - Incomplete certificate chain
                    - Mixed content blocking
                    """)
                    
                except Exception as e:
                    st.error(f"❌ Error checking SSL: {str(e)}")
                    st.info(f"💡 Try checking manually at: https://www.ssllabs.com/ssltest/analyze.html?d={domain_ssl}")
        else:
            st.warning("⚠️ Please enter a domain name")

elif tool == "📚 Help Center":
    st.title("📚 HostAfrica Knowledge Base")
    st.markdown("Search for guides and documentation")
    
    search_query = st.text_input(
        "Search knowledge base:",
        placeholder="e.g., email setup, dns, cpanel",
        help="Enter keywords to search the knowledge base"
    )
    
    if search_query:
        results = search_kb(search_query)
        
        if results:
            st.success(f"✅ Found {len(results)} relevant article(s)")
            
            for result in results:
                with st.expander(f"📄 {result['title']}", expanded=True):
                    st.markdown(f"**Category:** {result['category'].replace('_', ' ').title()}")
                    st.markdown(f"**Keywords:** {', '.join(result['keywords'][:5])}")
                    st.link_button("📖 Read Article", result['url'], use_container_width=True)
        else:
            st.info("No articles found. Try different keywords.")
    
    st.markdown("---")
    st.link_button("🌐 Browse Full Help Center", "https://help.hostafrica.com", use_container_width=True, type="primary")

elif tool == "🧹 Flush DNS Cache":
    st.title("🧹 Flush Google DNS Cache")
    st.markdown("Clear Google's DNS cache to force fresh lookups")
    
    st.markdown('<div class="info-box">', unsafe_allow_html=True)
    st.markdown("""
    **When to flush DNS cache:**
    - After changing nameservers
    - After updating DNS records
    - When experiencing DNS propagation issues
    - To force fresh DNS lookups
    """)
    st.markdown('</div>', unsafe_allow_html=True)
    
    st.link_button("🧹 Open Google DNS Cache Flush", "https://dns.google/cache", use_container_width=True, type="primary")

elif tool == "💬 AI Support Chat":
    st.title("💬 AI Support Assistant")
    st.markdown("Get instant help with technical support questions")
    
    if not GEMINI_API_KEY:
        st.error("⚠️ Gemini API key not configured")
        st.info("💡 Add 'GEMINI_API_KEY' to your Streamlit secrets to enable AI chat.")
    else:
        # Display chat history
        for message in st.session_state.chat_history:
            role = message['role']
            content = message['content']
            
            if role == 'user':
                st.markdown(f'<div class="info-box">👤 **You:** {content}</div>', unsafe_allow_html=True)
            else:
                st.markdown(f'<div class="success-box">🤖 **AI Assistant:** {content}</div>', unsafe_allow_html=True)
        
        # Chat input
        user_input = st.text_area(
            "Ask a question:",
            placeholder="e.g., How do I set up email forwarding in cPanel?",
            help="Ask any technical support question",
            key="chat_input"
        )
        
        col1, col2 = st.columns([1, 4])
        
        with col1:
            send_button = st.button("💬 Send", type="primary", use_container_width=True)
        
        with col2:
            clear_button = st.button("🗑️ Clear Chat", use_container_width=True)
        
        if clear_button:
            st.session_state.chat_history = []
            st.rerun()
        
        if send_button and user_input:
            # Add user message to history
            st.session_state.chat_history.append({
                'role': 'user',
                'content': user_input
            })
            
            with st.spinner("🤖 AI is thinking..."):
                try:
                    # Configure Gemini
                    model = genai.GenerativeModel('gemini-1.5-flash')
                    
                    # Create context-aware prompt
                    context = """You are a helpful HostAfrica technical support assistant. 
                    Provide clear, accurate, and friendly technical support answers.
                    Focus on HostAfrica services including cPanel, DirectAdmin, DNS, email, domains, and SSL.
                    Always be professional and helpful."""
                    
                    # Build conversation history for context
                    conversation = context + "\n\n"
                    for msg in st.session_state.chat_history[-5:]:  # Last 5 messages for context
                        conversation += f"{msg['role']}: {msg['content']}\n"
                    
                    # Generate response
                    response = model.generate_content(conversation)
                    ai_response = response.text
                    
                    # Add AI response to history
                    st.session_state.chat_history.append({
                        'role': 'assistant',
                        'content': ai_response
                    })
                    
                    st.rerun()
                    
                except Exception as e:
                    st.error(f"❌ Error: {str(e)}")
                    st.info("💡 Make sure your API key is valid and you have internet connection.")
