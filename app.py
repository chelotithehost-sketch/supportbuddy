# (Full file content follows)
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

# Custom CSS (Typography & Windows 11-like styling)
st.markdown("""
    <style>
    :root {
      /* Fluent / Windows 11 inspired palette */
      --win-accent-1: #0078D4;    /* primary blue */
      --win-accent-2: #2b88d8;    /* secondary blue */
      --win-muted: #64748b;       /* muted text */
      --win-bg-1: #f6f8fb;        /* subtle page background */
      --glass: rgba(255,255,255,0.60);
      --card-radius: 12px;
      --card-radius-large: 16px;
      --soft-shadow: 0 8px 24px rgba(16,24,40,0.06);
      --soft-shadow-strong: 0 14px 40px rgba(16,24,40,0.10);
    }

    /* Use Segoe UI Variable on Windows, fallback to Roboto/Inter/system UI */
    html, body, [class*="css"] {
      font-family: "Segoe UI Variable", "Segoe UI", Roboto, "Helvetica Neue", Inter, Arial, system-ui;
      -webkit-font-smoothing: antialiased;
      -moz-osx-font-smoothing: grayscale;
      color: #0f1724;
      background: var(--win-bg-1);
    }

    /* Fluid/responsive typography */
    html { font-size: 16px; }
    @media (max-width:1200px){ html { font-size:15px; } }
    @media (max-width:992px){  html { font-size:14px; } }
    @media (max-width:720px){  html { font-size:13px; } }

    .main { padding: 1rem 2rem; }

    /* Category Cards with Dynamic Colors */
    .category-card {
      padding: 1.5rem;
      border-radius: var(--card-radius-large);
      color: white;
      text-align: left;
      cursor: pointer;
      transition: transform 0.22s cubic-bezier(.2,.9,.3,1), box-shadow 0.22s ease, background 0.22s ease;
      margin: 1rem 0;
      min-height: 160px;
      display: flex;
      flex-direction: column;
      justify-content: center;
      position: relative;
      overflow: hidden;
      box-shadow: var(--soft-shadow);
      border: 1px solid rgba(15,23,42,0.04);
      background-blend-mode: overlay;
      backdrop-filter: blur(6px) saturate(120%);
    }

    /* Subtle acrylic overlay on hover */
    .category-card::before {
      content: '';
      position: absolute;
      top: 0;
      left: 0;
      right: 0;
      bottom: 0;
      background: linear-gradient(180deg, rgba(255,255,255,0.06), rgba(255,255,255,0.02));
      opacity: 0;
      transition: opacity 0.22s ease;
      pointer-events: none;
    }

    .category-card:hover {
      transform: translateY(-6px);
      box-shadow: var(--soft-shadow-strong);
    }

    .category-card:hover::before { opacity: 1; }

    .category-icon {
      font-size: 2.8rem;
      margin-bottom: 0.6rem;
      text-shadow: 0 6px 18px rgba(2,6,23,0.12);
      animation: float 4s ease-in-out infinite;
      line-height: 1;
    }

    @keyframes float {
      0%, 100% { transform: translateY(0px); }
      50% { transform: translateY(-6px); }
    }

    .category-title {
      font-size: 1.125rem; /* ~18px */
      font-weight: 700;
      margin-bottom: 0.25rem;
      color: #ffffff;
      letter-spacing: -0.2px;
    }

    .category-count {
      font-size: 0.85rem;
      opacity: 0.95;
      background: rgba(255,255,255,0.12);
      padding: 0.25rem 0.7rem;
      border-radius: 999px;
      display: inline-block;
      margin-top: 0.45rem;
      font-weight: 600;
      color: rgba(255,255,255,0.95);
    }

    .category-description {
      font-size: 0.9rem;
      opacity: 0.95;
      margin-top: 0.35rem;
      font-style: normal;
      color: rgba(255,255,255,0.92);
    }

    /* Search Box Styling with acrylic / blur */
    .search-container {
      background: linear-gradient(90deg, rgba(255,255,255,0.70), rgba(255,255,255,0.62));
      padding: 1.25rem;
      border-radius: var(--card-radius);
      margin-bottom: 1.25rem;
      box-shadow: var(--soft-shadow);
      border: 1px solid rgba(15,23,42,0.04);
      backdrop-filter: blur(8px) saturate(120%);
      color: #0f1724;
    }

    .search-icon { font-size: 1.75rem; margin-bottom: 0.5rem; }

    .search-result-card {
      background: #ffffff;
      border-left: 4px solid var(--win-accent-1);
      padding: 0.9rem;
      border-radius: 10px;
      margin-bottom: 0.5rem;
      transition: all 0.18s ease;
      box-shadow: 0 6px 18px rgba(2,6,23,0.04);
      display: flex;
      align-items: center;
      gap: 0.8rem;
    }

    .search-result-card:hover {
      transform: translateX(6px);
      box-shadow: 0 12px 30px rgba(2,6,23,0.06);
      border-left-width: 6px;
    }

    .search-tool-name {
      font-weight: 700;
      color: #0f1724;
      font-size: 1rem;
      margin-bottom: 0;
      line-height: 1.1;
    }

    .search-category-badge {
      display: inline-block;
      padding: 0.18rem 0.6rem;
      border-radius: 10px;
      background: #f1f5f9;
      color: var(--win-muted);
      font-size: 0.78rem;
      margin-top: 0.2rem;
      font-weight: 600;
    }

    .no-results {
      text-align: center;
      padding: 1.5rem;
      color: var(--win-muted);
      font-size: 1rem;
    }

    /* Tool Button Styling – Windows 11 rounded pill with accent */
    .tool-button {
      margin: 0.45rem 0;
      padding: 0.65rem 1.2rem;
      border-radius: 10px;
      background: linear-gradient(180deg, #ffffff 0%, #f7f9fc 100%);
      border: 1px solid rgba(15,23,42,0.04);
      cursor: pointer;
      transition: all 0.15s cubic-bezier(.2,.8,.2,1);
      font-weight: 600;
      color: #0f1724;
      box-shadow: 0 4px 10px rgba(2,6,23,0.03);
    }

    .tool-button:hover {
      background: linear-gradient(180deg, var(--win-accent-1), var(--win-accent-2));
      color: #ffffff;
      border-color: rgba(255,255,255,0.06);
      transform: translateY(-3px);
      box-shadow: 0 14px 40px rgba(15,76,212,0.12);
    }

    .tool-button:focus {
      outline: 3px solid rgba(0,120,212,0.12);
      outline-offset: 2px;
      border-radius: 10px;
    }

    /* Status Boxes: subtle rounded cards */
    .success-box, .warning-box, .error-box, .info-box {
      padding: 1.25rem;
      border-radius: 10px;
      margin: 1rem 0;
      box-shadow: 0 8px 28px rgba(2,6,23,0.03);
      border-left: 6px solid transparent;
    }

    .success-box {
      background: linear-gradient(180deg, #f0fdf4 0%, #ecfdf3 100%);
      border-left-color: #10b981;
    }

    .warning-box {
      background: linear-gradient(180deg, #fffbeb 0%, #fffbf0 100%);
      border-left-color: #f59e0b;
    }

    .error-box {
      background: linear-gradient(180deg, #fff1f2 0%, #fff4f6 100%);
      border-left-color: #ef4444;
    }

    .info-box {
      background: linear-gradient(180deg, #eef2ff 0%, #f8fafc 100%);
      border-left-color: var(--win-accent-1);
    }

    /* Stats Badge */
    .stats-badge {
      background: linear-gradient(90deg, var(--win-accent-1) 0%, var(--win-accent-2) 100%);
      color: white;
      padding: 0.8rem 1.6rem;
      border-radius: 12px;
      text-align: center;
      font-size: 1rem;
      box-shadow: 0 10px 36px rgba(15,76,212,0.10);
      margin: 1.6rem 0;
      font-weight: 700;
    }

    /* Breadcrumb */
    .breadcrumb {
      background: transparent;
      padding: 0.5rem 0.6rem;
      border-radius: 8px;
      margin-bottom: 1rem;
      font-size: 0.95rem;
      color: var(--win-muted);
    }

    /* Responsive adjustments */
    @media (max-width: 1024px) {
      .category-card { min-height: 150px; }
    }
    @media (max-width: 768px) {
      .category-icon { font-size: 2.2rem; }
      .category-title { font-size: 1rem; }
      .search-container { padding: 1rem; }
      .category-card { min-height: 140px; padding: 1rem; }
      .main { padding: 0.8rem 1rem; }
    }
    </style>
""", unsafe_allow_html=True)

# Session state initialization
if 'chat_history' not in st.session_state:
    st.session_state.chat_history = []
if 'session_notes' not in st.session_state:
    st.session_state.session_notes = ""
# Simplified navigation: only selected_tool is required
if 'selected_tool' not in st.session_state:
    st.session_state.selected_tool = None

# Define tool categories
# ============================================================================
# TOOL CATEGORIES WITH VISUAL IMPROVEMENTS
# ============================================================================

# Normalize CATEGORY_COLORS keys to match category names used in TOOL_CATEGORIES
CATEGORY_COLORS = {
    "Home": "linear-gradient(135deg, #667eea 0%, #764ba2 100%)",
    "Admin Links": "linear-gradient(135deg, #f093fb 0%, #f5576c 100%)",
    "Ticket Management": "linear-gradient(135deg, #4facfe 0%, #00f2fe 100%)",
    "AI Tools": "linear-gradient(135deg, #43e97b 0%, #38f9d7 100%)",
    "Domain & DNS": "linear-gradient(135deg, #fa709a 0%, #fee140 100%)",
    "WEB & SSL TOOLS": "linear-gradient(135deg, #30cfd0 0%, #330867 100%)",
    "Email": "linear-gradient(135deg, #a8edea 0%, #fed6e3 100%)",
    "Server & Database": "linear-gradient(135deg, #ff9a9e 0%, #fecfef 100%)",
    "Network": "linear-gradient(135deg, #ffecd2 0%, #fcb69f 100%)",
    "Utilities": "linear-gradient(135deg, #ff6e7f 0%, #bfe9ff 100%)"
}

TOOL_CATEGORIES = {
    "Admin Links": {
        "icon": "👨‍💼",
        "tools": [
            "🔐 PIN Checker",
            "🔓 IP Unban",
            "📝 Bulk NS Updater",
            "📋 cPanel Account List"
        ],
        "description": "Your essential admin tools",
        "color": CATEGORY_COLORS.get("Admin Links")
    },
    "Ticket Management": {
        "icon": "🎫",
        "tools": [
            "✅ Support Ticket Checklist",
            "🔍 AI Ticket Analysis",
            "🩺 Smart Symptom Checker"
        ],
        "description": "Let's analyse the tickets",
        "color": CATEGORY_COLORS.get("Ticket Management")
    },
    "AI Tools": {
        "icon": "🤖",
        "tools": [
            "💬 AI Support Chat",
            "📧 AI Mail Error Assistant",
            "❓ Error Code Explainer"
        ],
        "description": "AI tools for you",
        "color": CATEGORY_COLORS.get("AI Tools")
    },
    "Domain & DNS": {
        "icon": "🌐",
        "tools": [
            "🔍 Domain Status Check",
            "🔎 DNS Analyzer",
            "📋 NS Authority Checker",
            "🌍 WHOIS Lookup"
        ],
        "description": "Domain Tools",
        "color": CATEGORY_COLORS.get("Domain & DNS")
    },
    "WEB & SSL TOOLS": {
        "icon": "🌍",
        "tools": [
            "🔧 Web Error Troubleshooting",
            "🔒 SSL Certificate Checker",
            "🔀 HTTPS Redirect Test",
            "⚠️ Mixed Content Detector",
            "📊 HTTP Status Code Checker",
            "🔗 Redirect Checker"
        ],
        "description": "Web and SSL Tools for You",
        "color": CATEGORY_COLORS.get("WEB & SSL TOOLS")
    },
    "Email": {
        "icon": "📧",
        "tools": [
            "📮 MX Record Checker",
            "✉️ Email Account Tester",
            "🔒 SPF/DKIM Check",
            "📄 Email Header Analyzer"
        ],
        "description": "Essential Email Tools",
        "color": CATEGORY_COLORS.get("Email")
    },
    "Server & Database": {
        "icon": "💾",
        "tools": [
            "📊 Database Size Calculator",
            "🔐 File Permission Checker"
        ],
        "description": "Server Tools",
        "color": CATEGORY_COLORS.get("Server & Database")
    },
    "Network": {
        "icon": "📡",
        "tools": [
            "🔍 IP Address Lookup",
            "🗂️ DNS Analyzer",
            "🧹 Flush DNS Cache"
        ],
        "description": "Your Essential Network Tools",
        "color": CATEGORY_COLORS.get("Network")
    },
    "Utilities": {
        "icon": "🛠️",
        "tools": [
            "📚 Help Center",
            "🔑 Password Strength Meter",
            "📋 Copy-Paste Utilities",
            "📸 Screenshot Annotator",
            "📝 Session Notes",
            "🗑️ Clear Cache Instructions",
            "🧹 Flush DNS Cache"
        ],
        "description": "Utilities",
        "color": CATEGORY_COLORS.get("Utilities")
    }
}
    
# ============================================================================
# HELPER FUNCTIONS
# ============================================================================
def search_tools(query):
    """Search for tools across all categories"""
    query = query.lower().strip()
    results = []
    
    for category_name, category_info in TOOL_CATEGORIES.items():
        for tool in category_info['tools']:
            # Search in tool name
            if query in tool.lower():
                results.append({
                    'tool': tool,
                    'category': category_name,
                    'description': category_info['description'],
                    'icon': category_info['icon']
                })
            # Also search in category name
            elif query in category_name.lower():
                results.append({
                    'tool': tool,
                    'category': category_name,
                    'description': category_info['description'],
                    'icon': category_info['icon']
                })
    
    return results

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

# --- Specialized .ng Session & Utilities
ng_session = requests.Session()
ng_session.headers.update({"User-Agent": "Mozilla/5.0 SupportBuddy/1.0"})

def query_ng_whois(domain):
    """Query WHOIS information for .ng domains"""
    url = "https://whois.net.ng/whois/"
    try:
        response = ng_session.get(url, params={"domain": domain}, timeout=10)
        return response.text
    except Exception as e:
        return f"Error: {e}"

def parse_ng_whois_simplified(html):
    """
    Parse .ng WHOIS HTML - ONLY extract essential sections:
    - Domain Information
    - Registrar Information  
    - DNSSEC status (from Domain Information section)
    - Name Servers
    
    Returns a dictionary with only these 4 sections
    """
    soup = BeautifulSoup(html, 'html.parser')
    essential_sections = {}
    
    # Define which sections we want to capture
    target_sections = ['Domain Information', 'Registrar Information']
    
    # Find all WHOIS data cards
    cards = soup.find_all('div', class_='card mb-4')
    
    for card in cards:
        header = card.find('h5', class_='card-header whois_bg')
        if not header:
            continue
            
        section_name = header.text.strip()
        
        # Only process target sections
        if section_name in target_sections:
            data = {}
            table = card.find('table', class_='table')
            
            if table:
                for tr in table.find_all('tr'):
                    tds = tr.find_all('td')
                    if len(tds) == 2:
                        key = tds[0].text.strip().rstrip(':')
                        value = tds[1].get_text(separator=' ').strip()
                        data[key] = value
            
            essential_sections[section_name] = data
    
    return essential_sections
    
def display_ng_whois_simplified(domain):
    """Display only essential .ng WHOIS data"""
    html = query_ng_whois(domain)
    sections = parse_ng_whois_simplified(html)
    dnssec_status = get_dnssec_info(domain)
    ns_list = get_live_ns(domain)
    
    st.markdown("### 🇳🇬 Registration Data")
    
    if 'Domain Information' in sections:
        with st.expander("📋 Domain Information", expanded=True):
            cols = st.columns(2)
            for i, (k, v) in enumerate(sections['Domain Information'].items()):
                cols[i % 2].markdown(f"**{k}:** {v}")
    
    if 'Registrar Information' in sections:
        with st.expander("📋 Registrar Information", expanded=True):
            cols = st.columns(2)
            for i, (k, v) in enumerate(sections['Registrar Information'].items()):
                cols[i % 2].markdown(f"**{k}:** {v}")
    
    with st.expander("🛡️ DNSSEC Status", expanded=True):
        st.info(f"**Status:** {dnssec_status}")
    
    with st.expander("🌐 Name Servers", expanded=True):
        if ns_list:
            for ns in ns_list:
                st.code(ns)
        else:
            st.warning("No nameservers found")    

def get_dnssec_info(domain):
    """Get DNSSEC status - Info only"""
    try:
        url = f"https://dns.google/resolve?name={domain}&type=DS"
        res = requests.get(url, timeout=5).json()
        return "DNSSEC Signed" if "Answer" in res else "DNSSEC Unsigned"
    except:
        return "DNSSEC Unknown"

def get_live_ns(domain):
    """Direct NS lookup for live nameservers"""
    try:
        url = f"https://dns.google/resolve?name={domain}&type=NS"
        res = requests.get(url, timeout=5).json()
        if res.get('Status') == 0 and 'Answer' in res:
            return [r['data'].lower().rstrip('.') for r in res['Answer'] if r['type'] == 2]
    except:
        pass
    return []

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
    
# Knowledge Base Articles Database
HOSTAFRICA_KB = {
    'email': [
        {
            'title': 'DirectAdmin and cPanel Email',
            'url': 'https://help.hostafrica.com/category/control-panel-and-emails',
            'keywords': ['email', 'setup', 'imap', 'smtp', 'outlook', 'thunderbird', 'mail', 'configure', 'client']
        },
        {
            'title': 'HMail and Workspace',
            'url': 'https://help.hostafrica.com/category/professional-email-and-workspace',
            'keywords': ['Hmail', 'Professional Mail', 'email', 'setup', 'imap', 'smtp', 'outlook', 'thunderbird', 'mail', 'configure', 'client']
        }
    ],
    'domain': [
        {
            'title': 'How to Point Your Domain to HostAfrica',
            'url': 'https://help.hostafrica.com/category/domains',
            'keywords': ['domain', 'nameservers', 'dns', 'pointing', 'ns1', 'ns2', 'setup']
        },
        {
            'title': 'Understanding DNS Records (A, CNAME, MX, TXT)',
            'url': 'https://help.hostafrica.com/category/dns-and-nameservers',
            'keywords': ['dns', 'records', 'a record', 'cname', 'mx', 'txt', 'zone', 'propagation']
        },
        {
            'title': 'Domain Transfer Guide',
            'url': 'https://help.hostafrica.com/category/domains',
            'keywords': ['domain', 'transfer', 'epp', 'auth code', 'registrar', 'migrate']
        }
    ],
    'cpanel': [
        {
            'title': 'cPanel Getting Started Guide',
            'url': 'https://help.hostafrica.com/category/control-panel-and-emails/cpanel',
            'keywords': ['cpanel', 'getting started', 'basics', 'login', 'dashboard', 'control panel']
        },
        {
            'title': 'DirectAdmin Getting Started Guide',
            'url': 'https://help.hostafrica.com/category/control-panel-and-emails/directadmin',
            'keywords': ['DirectAdmin', 'getting started', 'basics', 'login', 'dashboard']
        }
    ],
    'ssl': [
        {
            'title': 'SSL Certificate',
            'url': 'https://help.hostafrica.com/category/ssl-certificates',
            'keywords': ['ssl', 'https', 'certificate', 'secure']
        }
    ],
    'wordpress': [
        {
            'title': 'WordPress',
            'url': 'https://help.hostafrica.com/category/wordpress',
            'keywords': ['wordpress', 'install', 'softaculous', 'one click', 'wp', 'setup']
        },
        {
            'title': 'Softaculous',
            'url': 'https://help.hostafrica.com/category/softaculous',
            'keywords': ['softaculous', 'one click']
        }
    ]
} 

# ============================================================================
# SINGLE-PAGE NAVIGATION RENDERER
# ============================================================================
def _sanitize_key(s: str) -> str:
    """Return a safe key fragment for Streamlit widget keys"""
    return re.sub(r'\W+', '_', s).strip('_')

def render_all_categories_and_tools():
    """Render a single page with all categories and their tools (grid of buttons)"""
    st.title("🔧 Support Buddy - Complete Toolkit")
    st.markdown("### All categories and tools — click a tool to open it")
    st.markdown("---")

    total_tools = sum(len(cat['tools']) for cat in TOOL_CATEGORIES.values())
    st.markdown(f"<div class='stats-badge'>📊 {total_tools} tools available</div>", unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)

    for category_name, category_info in TOOL_CATEGORIES.items():
        icon = category_info.get('icon', '')
        description = category_info.get('description', '')
        color = category_info.get('color', None)

        # Category header
        st.markdown(f"## {icon} {category_name}")
        if description:
            st.caption(description)

        tools = category_info.get('tools', [])
        num_cols = 4

        # Render tools in rows of num_cols
        for row_start in range(0, len(tools), num_cols):
            cols = st.columns(num_cols)
            for i in range(num_cols):
                tool_idx = row_start + i
                if tool_idx < len(tools):
                    tool = tools[tool_idx]
                    safe_cat = _sanitize_key(category_name)
                    # Unique key per category + index
                    btn_key = f"btn_{safe_cat}_{tool_idx}"
                    with cols[i]:
                        if st.button(tool, key=btn_key, use_container_width=True):
                            st.session_state.selected_tool = tool
                            st.rerun()

        st.markdown("---")

# ============================================================================
# MAIN APP ROUTING (SINGLE-STATE: selected_tool only)
# ============================================================================
if st.session_state.selected_tool is None:
    # Show all categories with their tools on a single page
    render_all_categories_and_tools()

else:
    # Show the selected tool (existing implementations reused)
    tool = st.session_state.selected_tool

    # Back button
    if st.button("← Back to All Tools", key="back_to_all_tools"):
        st.session_state.selected_tool = None
        st.rerun()

    # ============================================================================
    # MAIN CONTENT - TOOL IMPLEMENTATIONS (unchanged, uses 'tool' variable)
    # ============================================================================

    if tool == "🔐 PIN Checker":
        st.title("🔐 PIN Checker")
        st.markdown("Verify customer PINs for secure account access and verification.")
        
        col1, col2 = st.columns([3, 1])
        with col1:
            st.info("Check the provided customer PIN against the WHMCS records.")
        with col2:
            st.link_button("Open Tool", "https://my.hostafrica.com/admin/admin_tool/client-pin", use_container_width=True)

    elif tool == "🔓 IP Unban":
        st.title("🔓 IP Unban")
        st.markdown("Search for and remove IP addresses from server firewalls.")
        
        col1, col2 = st.columns([3, 1])
        with col1:
            st.info("Use this to quickly unblock clients who are locked out.")
        with col2:
            st.link_button(
                "Open Tool",
                "https://my.hostafrica.com/admin/custom/scripts/unban/",
                use_container_width=True
            )

    elif tool == "📝 Bulk NS Updater":
        st.title("📝 Bulk Nameserver Updater")
        st.markdown("Update nameservers for multiple domains simultaneously in WHMCS.")
        
        col1, col2 = st.columns([3, 1])
        with col1:
            st.info("Save time by modifying NS records for domain batches.")
        with col2:
            st.link_button(
                "🔄 Open Updater",
                "https://my.hostafrica.com/admin/addonmodules.php?module=nameserv_changer",
                use_container_width=True
            )

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
                            
                            # WHOIS Information - handles both .ng and other TLDs
                            st.markdown("### 📋 WHOIS Information")
                            
                            # Check if it's a .ng domain
                            if domain.endswith('.ng'):
                                # Use the .ng specific WHOIS
                                html = query_ng_whois(domain)
                                sections = parse_ng_whois_simplified(html)
                                
                                if sections:
                                    info_col1, info_col2 = st.columns(2)
                                    
                                    with info_col1:
                                        # Get registrar from Registrar Information
                                        if 'Registrar Information' in sections:
                                            reg_info = sections['Registrar Information']
                                            if 'Registrar' in reg_info:
                                                st.info(f"**Registrar:** {reg_info['Registrar']}")
                                        
                                        # Get created date from Domain Information
                                        if 'Domain Information' in sections:
                                            dom_info = sections['Domain Information']
                                            if 'Registered On' in dom_info:
                                                st.info(f"**Created:** {dom_info['Registered On']}")
                                    
                                    with info_col2:
                                        # Get expiration from Domain Information
                                        if 'Domain Information' in sections:
                                            dom_info = sections['Domain Information']
                                            if 'Expires On' in dom_info:
                                                st.info(f"**Expires:** {dom_info['Expires On']}")
                                            if 'Status' in dom_info:
                                                st.info(f"**Status:** {dom_info['Status']}")
                                else:
                                    st.warning("⚠️ Could not retrieve .ng WHOIS data")
                            
                            else:
                                # Use standard WHOIS for other TLDs
                                if WHOIS_AVAILABLE:
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
                                else:
                                    st.warning("⚠️ WHOIS library not available")

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
        st.title("🌍 WHOIS & Health Check")
        st.markdown("Detailed registration analysis with status-aware reporting.")
        
        domain_input = st.text_input("Enter domain name:", placeholder="hostafrica.co.za or .ng", key="whois_main_input")
        
        if st.button("🔍 Run Analysis", type="primary"):
            if domain_input:
                domain = domain_input.strip().lower().replace('https://', '').replace('http://', '').split('/')[0]
                
                with st.spinner(f"Analyzing {domain}..."):
                    dnssec_status = get_dnssec_info(domain)
                    ns_list = get_live_ns(domain)
                    now = datetime.now().replace(tzinfo=None)  # Timezone-neutral for comparison
                    
                    try:
                        # ==========================================
                        # UNIQUE .ng TREATMENT
                        # ==========================================
                        if domain.endswith('.ng'):
                            display_ng_whois_simplified(domain)
                        
                        # ==========================================
                        # STANDARD TLD TREATMENT (.com, .net, .org, etc)
                        # ==========================================
                        else:
                            w = whois.whois(domain)
                            
                            # Consolidate status to string for logic check
                            status_list = w.status if isinstance(w.status, list) else [w.status]
                            status_joined = " ".join([str(s) for s in status_list]).lower()
                            
                            # Fix: Handle naive/aware datetime comparison
                            is_expired = False
                            if w.expiration_date:
                                exp = w.expiration_date[0] if isinstance(w.expiration_date, list) else w.expiration_date
                                # Remove timezone info from registry date to match local now()
                                if exp.replace(tzinfo=None) < now:
                                    is_expired = True
                            
                            # Status-Aware Alerting Logic
                            error_keywords = ["hold", "suspended", "expired", "redemption", "pendingdelete", "raa"]
                            if any(x in status_joined for x in error_keywords) or is_expired:
                                st.error(f"❌ Domain Alert: {status_joined.upper() if status_joined else 'EXPIRED'}")
                            elif "ok" in status_joined or "active" in status_joined:
                                st.success("✅ Domain Status: OK / ACTIVE")
                            else:
                                st.info(f"ℹ️ Current Status: {status_joined.upper()}")
                            
                            # Display registration details
                            st.markdown("### 📋 WHOIS Information")
                            col1, col2 = st.columns(2)
                            with col1:
                                st.markdown("**Registration Details:**")
                                st.write(f"**Domain:** {w.domain_name if hasattr(w, 'domain_name') else 'N/A'}")
                                st.write(f"**Registrar:** {w.registrar if hasattr(w, 'registrar') else 'N/A'}")
                            
                            with col2:
                                st.markdown("**Important Dates:**")
                                if w.expiration_date:
                                    exp = w.expiration_date[0] if isinstance(w.expiration_date, list) else w.expiration_date
                                    st.write(f"**Expires:** {str(exp).split()[0]}")
                                    
                                    # Quick Health Check
                                    try:
                                        days_left = (exp.replace(tzinfo=None) - datetime.now()).days
                                        if days_left < 30:
                                            st.warning(f"⚠️ Expires in {days_left} days!")
                                        else:
                                            st.success(f"✅ {days_left} days remaining")
                                    except:
                                        pass
                            
                            with st.expander("📄 View Full WHOIS Output", expanded=False):
                                st.code(str(w), language=None)
                        
                        # ==========================================
                        # COMMON FOOTER (Neutral DNSSEC & Live NS)
                        # ==========================================
                        # ==========================================
                        # COMMON FOOTER (Only for non-.ng domains)
                        # ==========================================
                        if not domain.endswith('.ng'):
                            st.markdown("---")
                            c1, c2 = st.columns(2)
                            with c1:
                                st.info(f"🛡️ {dnssec_status}")
                            with c2:
                                st.write("**Live Nameservers:**")
                                if ns_list:
                                    for ns in ns_list:
                                        st.write(f"- `{ns}`")
                                else:
                                    st.warning("No nameservers found.")
                            
                    except Exception as e:
                        st.error(f"❌ Analysis failed: {str(e)}")
                        st.info(f"**Try manual lookup:**\n- https://who.is/whois/{domain}\n- https://lookup.icann.org/en/lookup?name={domain}")
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

    # WEB & SSL TOOLS
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
                    # Parse HTML to find resources
                    from bs4 import BeautifulSoup
                    soup = BeautifulSoup(response.text, 'html.parser')
                    
                    # Find all resources with src or href attributes
                    mixed_content = {
                        'images': [],
                        'scripts': [],
                        'stylesheets': [],
                        'iframes': [],
                        'links': [],
                        'other': []
                    }
                    
                    # Check images
                    for img in soup.find_all('img', src=True):
                        if img['src'].startswith('http://'):
                            mixed_content['images'].append(img['src'])
                    
                    # Check scripts
                    for script in soup.find_all('script', src=True):
                        if script['src'].startswith('http://'):
                            mixed_content['scripts'].append(script['src'])
                    
                    # Check stylesheets
                    for link in soup.find_all('link', href=True):
                        if link.get('rel') and 'stylesheet' in link['rel']:
                            if link['href'].startswith('http://'):
                                mixed_content['stylesheets'].append(link['href'])
                    
                    # Check iframes
                    for iframe in soup.find_all('iframe', src=True):
                        if iframe['src'].startswith('http://'):
                            mixed_content['iframes'].append(iframe['src'])
                    
                    # Check other links
                    for link in soup.find_all('a', href=True):
                        if link['href'].startswith('http://'):
                            mixed_content['links'].append(link['href'])
                    
                    # Check for other HTTP references in attributes
                    for tag in soup.find_all(True):
                        for attr, value in tag.attrs.items():
                            if isinstance(value, str) and value.startswith('http://'):
                                if attr not in ['src', 'href']:  # Already checked these
                                    mixed_content['other'].append(f"{tag.name}[{attr}]: {value}")
                    
                    # Count total mixed content
                    total_mixed = sum(len(v) for v in mixed_content.values())
                    
                    # Also count HTTPS resources for comparison
                    https_count = response.text.count('https://')
                    
                    # Display summary
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("HTTP Resources (Mixed)", total_mixed)
                    with col2:
                        st.metric("HTTPS Resources", https_count)
                    with col3:
                        if total_mixed > 0:
                            st.metric("Security Status", "⚠️ Issues Found", delta_color="inverse")
                        else:
                            st.metric("Security Status", "✅ Secure", delta_color="normal")
                    
                    # Display results
                    if total_mixed > 0:
                        st.error(f"⚠️ Found {total_mixed} HTTP resource(s) that should be HTTPS")
                        st.info("💡 Mixed content can cause browser warnings and security issues")
                        
                        # Show details for each type
                        if mixed_content['images']:
                            with st.expander(f"🖼️ Images ({len(mixed_content['images'])})", expanded=True):
                                for img in mixed_content['images']:
                                    st.code(img, language=None)
                        
                        if mixed_content['scripts']:
                            with st.expander(f"📜 Scripts ({len(mixed_content['scripts'])})", expanded=True):
                                st.warning("⚠️ Scripts are critical security issues!")
                                for script in mixed_content['scripts']:
                                    st.code(script, language=None)
                        
                        if mixed_content['stylesheets']:
                            with st.expander(f"🎨 Stylesheets ({len(mixed_content['stylesheets'])})", expanded=True):
                                for css in mixed_content['stylesheets']:
                                    st.code(css, language=None)
                        
                        if mixed_content['iframes']:
                            with st.expander(f"🖼️ iFrames ({len(mixed_content['iframes'])})", expanded=True):
                                st.warning("⚠️ iFrames are critical security issues!")
                                for iframe in mixed_content['iframes']:
                                    st.code(iframe, language=None)
                        
                        if mixed_content['links']:
                            with st.expander(f"🔗 Links ({len(mixed_content['links'])})", expanded=False):
                                # Show only first 20 to avoid overwhelming display
                                for link in mixed_content['links'][:20]:
                                    st.code(link, language=None)
                                if len(mixed_content['links']) > 20:
                                    st.info(f"... and {len(mixed_content['links']) - 20} more links")
                        
                        if mixed_content['other']:
                            with st.expander(f"🔧 Other Resources ({len(mixed_content['other'])})", expanded=False):
                                for item in mixed_content['other']:
                                    st.code(item, language=None)
                        
                        # Provide fix suggestions
                        st.markdown("---")
                        st.markdown("### 🔧 How to Fix:")
                        st.markdown("""
                        1. **Replace** `http://` with `https://` in all resource URLs
                        2. **Use protocol-relative URLs**: `//example.com/style.css` (inherits page protocol)
                        3. **Host resources locally** if external HTTPS version is unavailable
                        4. **Update CMS/theme settings** to force HTTPS for all resources
                        5. **Check .htaccess or web.config** for mixed content rules
                        """)
                    else:
                        st.success("✅ No mixed content detected - all resources use HTTPS!")
                        st.balloons()

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

# NETWORK TOOLS
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
    
# SERVER TOOLS
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
     st.title("📚 HostAfrica Knowledge Base")
     st.markdown("Search our comprehensive knowledge base for guides and documentation")
    
     # Search input
     search_query = st.text_input(
        "🔍 Search:",
        placeholder="e.g., email setup, dns, cpanel, ssl certificate",
        help="Enter keywords to search the knowledge base"
    )
    
    if search_query:
        results = search_kb(search_query)
        
        if results:
            st.success(f"✅ Found {len(results)} relevant article(s)")
            
            for idx, result in enumerate(results, 1):
                with st.expander(f"📄 {result['title']}", expanded=(idx <= 3)):
                    col1, col2 = st.columns([3, 1])
                    
                    with col1:
                        st.markdown(f"**Category:** {result['category'].replace('_', ' ').title()}")
                        st.markdown(f"**Related Topics:** {', '.join(result['keywords'][:6])}")
                    
                    with col2:
                        st.link_button("📖 Read", result['url'], use_container_width=True)
        else:
            st.info("💡 No articles found. Try different keywords or browse categories below.")
    
    # Popular Categories
    st.markdown("---")
    st.markdown("### 📂 Browse by Category")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        if st.button("📧 Email", use_container_width=True):
            st.session_state.kb_category = 'email'
        if st.button("🌐 Domain & DNS", use_container_width=True):
            st.session_state.kb_category = 'domain'
    
    with col2:
        if st.button("🔧 cPanel", use_container_width=True):
            st.session_state.kb_category = 'cpanel'
        if st.button("🔒 SSL & HTTPS", use_container_width=True):
            st.session_state.kb_category = 'ssl'
    
    with col3:
        if st.button("💻 WordPress", use_container_width=True):
            st.session_state.kb_category = 'wordpress'
        if st.button("📁 FTP", use_container_width=True):
            st.session_state.kb_category = 'ftp'
    
    with col4:
        if st.button("💳 Billing", use_container_width=True):
            st.session_state.kb_category = 'billing'
        if st.button("🔍 Troubleshooting", use_container_width=True):
            st.session_state.kb_category = 'troubleshooting'
    
    # Show category articles if selected
    if 'kb_category' in st.session_state:
        category = st.session_state.kb_category
        st.markdown(f"### {category.title()} Articles")
        
        for article in HOSTAFRICA_KB.get(category, []):
            with st.expander(f"📄 {article['title']}"):
                st.markdown(f"**Keywords:** {', '.join(article['keywords'][:8])}")
                st.link_button("📖 Read Article", article['url'], use_container_width=True)
    
    st.markdown("---")
    st.link_button("🌐 Browse Full Help Center", "https://help.hostafrica.com", use_container_width=True, type="primary")

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
        
        **Manual Method:**
        1. Click the three dots (⋮) in the top-right corner
        2. Go to **More tools** → **Clear browsing data**
        3. Select **Advanced** tab
        4. Choose time range: **All time**
        5. Check **Cached images and files**
        6. Click **Clear data**
        
        **Hard Refresh (for current page only):**
        - Windows/Linux: `Ctrl+F5` or `Ctrl+Shift+R`
        - Mac: `Cmd+Shift+R`
        """)
    
    elif browser == "Firefox":
        st.markdown("""
        ### Mozilla Firefox
        
        **Quick Method:**
        1. Press `Ctrl+Shift+Delete` (Windows/Linux) or `Cmd+Shift+Delete` (Mac)
        2. Select "Everything" from time range
        3. Check "Cache"
        4. Click "Clear Now"
        
        **Manual Method:**
        1. Click the hamburger menu (☰) in the top-right corner
        2. Go to **Settings**
        3. Click **Privacy & Security** in the left sidebar
        4. Scroll to **Cookies and Site Data**
        5. Click **Clear Data...**
        6. Check **Cached Web Content**
        7. Click **Clear**
        
        **Hard Refresh (for current page only):**
        - Windows/Linux: `Ctrl+F5` or `Ctrl+Shift+R`
        - Mac: `Cmd+Shift+R`
        """)
    
    elif browser == "Safari":
        st.markdown("""
        ### Safari (macOS)
        
        **Quick Method:**
        1. Press `Cmd+Option+E` to empty cache
        2. Or go to **Develop** → **Empty Caches**
        
        **Enable Develop Menu (if not visible):**
        1. Go to **Safari** → **Preferences**
        2. Click **Advanced** tab
        3. Check "Show Develop menu in menu bar"
        
        **Manual Method:**
        1. Go to **Safari** → **Preferences**
        2. Click **Advanced** tab
        3. Enable "Show Develop menu in menu bar"
        4. Click **Develop** in menu bar
        5. Select **Empty Caches**
        
        **Clear All History & Cache:**
        1. Go to **Safari** → **Clear History...**
        2. Select "all history" from dropdown
        3. Click **Clear History**
        
        **Hard Refresh (for current page only):**
        - Mac: `Cmd+Option+R` or `Cmd+Shift+R`
        
        **Safari (iOS - iPhone/iPad):**
        1. Go to **Settings** → **Safari**
        2. Scroll down and tap **Clear History and Website Data**
        3. Confirm by tapping **Clear History and Data**
        """)
    
    elif browser == "Edge":
        st.markdown("""
        ### Microsoft Edge
        
        **Quick Method:**
        1. Press `Ctrl+Shift+Delete` (Windows) or `Cmd+Shift+Delete` (Mac)
        2. Select "All time" from time range
        3. Check "Cached images and files"
        4. Click "Clear now"
        
        **Manual Method:**
        1. Click the three dots (...) in the top-right corner
        2. Go to **Settings**
        3. Click **Privacy, search, and services** in the left sidebar
        4. Under "Clear browsing data", click **Choose what to clear**
        5. Select time range: **All time**
        6. Check **Cached images and files**
        7. Click **Clear now**
        
        **Hard Refresh (for current page only):**
        - Windows: `Ctrl+F5` or `Ctrl+Shift+R`
        - Mac: `Cmd+Shift+R`
        """)
    
    elif browser == "Opera":
        st.markdown("""
        ### Opera
        
        **Quick Method:**
        1. Press `Ctrl+Shift+Delete` (Windows/Linux) or `Cmd+Shift+Delete` (Mac)
        2. Select "All time" from time range
        3. Check "Cached images and files"
        4. Click "Clear data"
        
        **Manual Method:**
        1. Click the **Opera menu** (O icon) in the top-left corner
        2. Go to **Settings** (or press `Alt+P`)
        3. Click **Privacy & security** in the left sidebar
        4. Under "Privacy", click **Clear browsing data**
        5. Select **Advanced** tab
        6. Choose time range: **All time**
        7. Check **Cached images and files**
        8. Click **Clear data**
        
        **Hard Refresh (for current page only):**
        - Windows/Linux: `Ctrl+F5` or `Ctrl+Shift+R`
        - Mac: `Cmd+Shift+R`
        """)
    
    # Common tips for all browsers
    st.markdown("---")
    st.markdown("### 💡 Additional Tips")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.info("""
        **Why Clear Cache?**
        - Fix loading issues
        - See website updates
        - Resolve display problems
        - Free up disk space
        - Troubleshoot errors
        """)
    
    with col2:
        st.warning("""
        **What Gets Deleted:**
        - Cached images
        - Cached files
        - Temporary data
        
        **What Stays:**
        - Passwords (unless selected)
        - Bookmarks
        - History (unless selected)
        """)
    
    st.markdown("---")
    st.markdown("### 🔄 Incognito/Private Mode Alternative")
    st.markdown("""
    If you just want to test without cache:
    - **Chrome**: `Ctrl+Shift+N` (Windows) or `Cmd+Shift+N` (Mac)
    - **Firefox**: `Ctrl+Shift+P` (Windows) or `Cmd+Shift+P` (Mac)
    - **Safari**: `Cmd+Shift+N` (Mac)
    - **Edge**: `Ctrl+Shift+N` (Windows) or `Cmd+Shift+N` (Mac)
    - **Opera**: `Ctrl+Shift+N` (Windows) or `Cmd+Shift+N` (Mac)
    """)
