import streamlit as st
import requests
import json
from datetime import datetime, timezone
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

# Configure Gemini API
GEMINI_API_KEY = ""
try:
    GEMINI_API_KEY = st.secrets.get("GEMINI_API_KEY", "")
    if GEMINI_API_KEY:
        import google.generativeai as genai
        genai.configure(api_key=GEMINI_API_KEY)
except:
    pass

# Session state
if 'chat_history' not in st.session_state:
    st.session_state.chat_history = []
if 'session_notes' not in st.session_state:
    st.session_state.session_notes = ""

# Helper Functions
def get_client_ip():
    try:
        response = requests.get('https://api.ipify.org?format=json', timeout=5)
        return response.json()['ip']
    except:
        return "Unable to determine"

def check_password_strength(password):
    score = 0
    feedback = []
    if len(password) >= 8: score += 1
    else: feedback.append("Use at least 8 characters")
    if len(password) >= 12: score += 1
    if re.search(r'[a-z]', password): score += 1
    else: feedback.append("Add lowercase letters")
    if re.search(r'[A-Z]', password): score += 1
    else: feedback.append("Add uppercase letters")
    if re.search(r'\d', password): score += 1
    else: feedback.append("Add numbers")
    if re.search(r'[!@#$%^&*(),.?":{}|<>]', password): score += 1
    else: feedback.append("Add special characters")
    
    if score <= 2: strength, color = "Weak", "error"
    elif score <= 4: strength, color = "Moderate", "warning"
    else: strength, color = "Strong", "success"
    return strength, score, feedback, color

# Sidebar Navigation
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

# Tool selection
if category == "🏠 Home":
    tool = "Home"
elif category == "👨‍💼 Admin Links":
    tool = st.sidebar.radio("Admin Tools", ["🔐 PIN Checker", "🔓 IP Unban", "📝 Bulk NS Updater", "📋 cPanel Account List"])
elif category == "🎫 Ticket Management":
    tool = st.sidebar.radio("Ticket Tools", ["✅ Support Ticket Checklist", "🔍 AI Ticket Analysis", "🩺 Smart Symptom Checker"])
elif category == "🤖 AI Tools":
    tool = st.sidebar.radio("AI Assistants", ["💬 AI Support Chat", "📧 AI Mail Error Assistant", "❗ Error Code Explainer"])
elif category == "🌐 Domain & DNS":
    tool = st.sidebar.radio("Domain Tools", ["🔍 Domain Status Check", "🔎 DNS Analyzer", "🔍 NS Authority Checker", "📊 WHOIS Lookup"])
elif category == "📧 Email":
    tool = st.sidebar.radio("Email Tools", ["📮 MX Record Checker", "✉️ Email Account Tester", "🔐 SPF/DKIM Check", "📄 Email Header Analyzer"])
elif category == "🌍 Web & HTTP":
    tool = st.sidebar.radio("Web Tools", ["🔧 Web Error Troubleshooting", "🔒 SSL Certificate Checker", "🔀 HTTPS Redirect Test", "⚠️ Mixed Content Detector", "📊 HTTP Status Code Checker", "🔗 Redirect Checker", "🤖 robots.txt Viewer", "⚡ Website Speed Test"])
elif category == "📡 Network":
    tool = st.sidebar.radio("Network Tools", ["🌐 My IP Address", "📡 Ping Tool", "🔌 Port Checker", "🗺️ Traceroute"])
elif category == "💾 Server & Database":
    tool = st.sidebar.radio("Server Tools", ["🗄️ MySQL Connection Tester", "📊 Database Size Calculator", "📁 FTP Connection Tester", "🔐 File Permission Checker"])
elif category == "🛠️ Utilities":
    tool = st.sidebar.radio("Utilities", ["📚 Help Center", "🔑 Password Strength Meter", "🌍 Timezone Converter", "📋 Copy-Paste Utilities", "📸 Screenshot Annotator", "📝 Session Notes", "🗑️ Clear Cache Instructions", "🧹 Flush DNS Cache"])

# Main Content
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

elif tool == "🔐 PIN Checker":
    st.title("🔐 PIN Checker")
    st.markdown("Verify customer PINs for account access")
    col1, col2 = st.columns(2)
    with col1:
        customer_pin = st.text_input("Customer PIN:", type="password")
    with col2:
        account_pin = st.text_input("Account PIN:", type="password")
    if st.button("🔍 Verify PIN", type="primary"):
        if customer_pin and account_pin:
            if customer_pin == account_pin:
                st.success("✅ PIN verified! Access granted.")
            else:
                st.error("❌ PIN does not match!")
        else:
            st.warning("⚠️ Please enter both PINs")

elif tool == "🔓 IP Unban":
    st.title("🔓 IP Unban Tool")
    ip_address = st.text_input("IP Address:", placeholder="192.168.1.1")
    reason = st.text_area("Reason:", placeholder="Customer confirmed legitimate access")
    if st.button("🔓 Generate Unban Command", type="primary"):
        if ip_address and reason:
            st.success("### Command:")
            st.code(f"csf -dr {ip_address}")
            st.info(f"Log: Unbanned {ip_address}. Reason: {reason}")

elif tool == "📝 Bulk NS Updater":
    st.title("📝 Bulk Nameserver Updater")
    domains_input = st.text_area("Domains (one per line):", height=150)
    col1, col2 = st.columns(2)
    with col1:
        ns1 = st.text_input("Nameserver 1:")
        ns3 = st.text_input("Nameserver 3 (Optional):")
    with col2:
        ns2 = st.text_input("Nameserver 2:")
        ns4 = st.text_input("Nameserver 4 (Optional):")
    if st.button("📋 Generate Commands", type="primary"):
        if domains_input and ns1 and ns2:
            domains = [d.strip() for d in domains_input.split('\n') if d.strip()]
            st.success(f"Commands for {len(domains)} domain(s)")
            for domain in domains:
                nameservers = [ns for ns in [ns1, ns2, ns3, ns4] if ns]
                st.code(f"{domain}: {', '.join(nameservers)}")

elif tool == "📋 cPanel Account List":
    st.title("📋 cPanel Account List")
    st.code("cat /etc/trueuserdomains | cut -d: -f1 | sort")
    account_list = st.text_area("Paste Account List:", height=200)
    if account_list:
        accounts = [line.strip() for line in account_list.split('\n') if line.strip()]
        st.success(f"✅ Found {len(accounts)} accounts")
        search = st.text_input("🔍 Search:")
        if search:
            filtered = [acc for acc in accounts if search.lower() in acc.lower()]
            for acc in filtered: st.code(acc)
        else:
            for acc in accounts[:50]: st.code(acc)

elif tool == "✅ Support Ticket Checklist":
    st.title("✅ Support Ticket Checklist")
    checks = []
    st.markdown("### 📋 Basic Information")
    checks.append(st.checkbox("Customer verified"))
    checks.append(st.checkbox("Domain identified"))
    checks.append(st.checkbox("Issue clear"))
    st.markdown("### 🔧 Technical Details")
    checks.append(st.checkbox("Error messages collected"))
    checks.append(st.checkbox("Screenshots attached"))
    checks.append(st.checkbox("Steps documented"))
    st.markdown("### 🔐 Account Access")
    checks.append(st.checkbox("Credentials verified"))
    checks.append(st.checkbox("PIN checked"))
    st.markdown("### 🔍 Investigation")
    checks.append(st.checkbox("DNS checked"))
    checks.append(st.checkbox("Server verified"))
    st.markdown("### 📝 Response")
    checks.append(st.checkbox("Solution identified"))
    checks.append(st.checkbox("Response drafted"))
    
    completed = sum(checks)
    total = len(checks)
    st.progress(completed / total)
    st.info(f"Progress: {completed}/{total} ({completed/total*100:.0f}%)")

elif tool == "🔍 AI Ticket Analysis":
    st.title("🔍 AI Ticket Analysis")
    if not GEMINI_API_KEY:
        st.error("⚠️ API key not configured")
    else:
        uploaded_file = st.file_uploader("Upload Screenshot:", type=['png', 'jpg', 'jpeg'])
        ticket_text = st.text_area("Or paste text:", height=200)
        if st.button("🔍 Analyze", type="primary"):
            if uploaded_file or ticket_text:
                with st.spinner("Analyzing..."):
                    try:
                        model = genai.GenerativeModel('gemini-2.0-flash-exp')
                        prompt = """Analyze this support ticket and provide:
                        1. Issue Summary
                        2. Category
                        3. Severity
                        4. Key Information
                        5. Missing Information
                        6. Troubleshooting Steps
                        7. Recommended Tools
                        8. Estimated Time"""
                        
                        if uploaded_file:
                            image = Image.open(uploaded_file)
                            response = model.generate_content([prompt, image])
                        else:
                            response = model.generate_content(f"{prompt}\n\n{ticket_text}")
                        
                        st.markdown("### 🤖 Analysis:")
                        st.markdown(response.text)
                    except Exception as e:
                        st.error(f"Error: {e}")

elif tool == "🩺 Smart Symptom Checker":
    st.title("🩺 Smart Symptom Checker")
    if not GEMINI_API_KEY:
        st.error("⚠️ API key not configured")
    else:
        symptom = st.text_area("Describe the issue:", height=150)
        col1, col2 = st.columns(2)
        with col1:
            service = st.selectbox("Service:", ["Website", "Email", "Domain", "Database", "Other"])
        with col2:
            when = st.selectbox("When:", ["Just now", "Today", "Yesterday", "This week"])
        
        if st.button("🩺 Diagnose", type="primary"):
            if symptom:
                with st.spinner("Diagnosing..."):
                    try:
                        model = genai.GenerativeModel('gemini-3-flash-preview')
                        prompt = f"""Analyze: {symptom}, Service: {service}, When: {when}
                        
                        Provide:
                        1. Likely Causes
                        2. Immediate Checks
                        3. Recommended Tools
                        4. Step-by-Step Diagnosis
                        5. Common Solutions
                        6. Escalation Signs"""
                        
                        response = model.generate_content(prompt)
                        st.markdown("### 🩺 Diagnosis:")
                        st.markdown(response.text)
                    except Exception as e:
                        st.error(f"Error: {e}")

elif tool == "💬 AI Support Chat":
    st.title("💬 AI Support Chat")
    if not GEMINI_API_KEY:
        st.error("⚠️ API key not configured")
    else:
        for msg in st.session_state.chat_history:
            if msg['role'] == 'user':
                st.markdown(f'<div class="info-box">👤 {msg["content"]}</div>', unsafe_allow_html=True)
            else:
                st.markdown(f'<div class="success-box">🤖 {msg["content"]}</div>', unsafe_allow_html=True)
        
        user_input = st.text_area("Ask:", placeholder="How do I...?")
        col1, col2 = st.columns([1, 4])
        with col1:
            if st.button("💬 Send", type="primary"):
                if user_input:
                    st.session_state.chat_history.append({'role': 'user', 'content': user_input})
                    with st.spinner("Thinking..."):
                        try:
                            model = genai.GenerativeModel('gemini-3-flash-preview')
                            context = "You are a technical support assistant. Provide clear, helpful answers about hosting, cPanel, DNS, email, domains, and SSL."
                            conversation = context + "\n\n" + "\n".join([f"{m['role']}: {m['content']}" for m in st.session_state.chat_history[-10:]])
                            response = model.generate_content(conversation)
                            st.session_state.chat_history.append({'role': 'assistant', 'content': response.text})
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error: {e}")
        with col2:
            if st.button("🗑️ Clear"):
                st.session_state.chat_history = []
                st.rerun()

elif tool == "📧 AI Mail Error Assistant":
    st.title("📧 AI Mail Error Assistant")
    if not GEMINI_API_KEY:
        st.error("⚠️ API key not configured")
    else:
        error_msg = st.text_area("Email Error Message:", height=200)
        if st.button("🔍 Analyze", type="primary"):
            if error_msg:
                with st.spinner("Analyzing..."):
                    try:
                        model = genai.GenerativeModel('gemini-3-flash-preview')
                        prompt = f"""Analyze this email error:

{error_msg}

Provide:
1. Error Type
2. Plain English Explanation
3. Root Cause
4. Solutions (step-by-step)
5. Prevention Tips"""
                        response = model.generate_content(prompt)
                        st.markdown("### 🤖 Analysis:")
                        st.markdown(response.text)
                    except Exception as e:
                        st.error(f"Error: {e}")

elif tool == "❗ Error Code Explainer":
    st.title("❗ Error Code Explainer")
    if not GEMINI_API_KEY:
        st.error("⚠️ API key not configured")
    else:
        error_code = st.text_input("Error Code:", placeholder="500 Internal Server Error")
        context = st.text_area("Context (optional):", height=100)
        if st.button("🔍 Explain", type="primary"):
            if error_code:
                with st.spinner("Looking up..."):
                    try:
                        model = genai.GenerativeModel('gemini-3-flash-preview')
                        prompt = f"""Explain: {error_code}
{f"Context: {context}" if context else ""}

Provide:
1. What It Means
2. Common Causes
3. How to Fix
4. How to Diagnose
5. Prevention"""
                        response = model.generate_content(prompt)
                        st.markdown("### 🤖 Explanation:")
                        st.markdown(response.text)
                    except Exception as e:
                        st.error(f"Error: {e}")

elif tool == "🔍 Domain Status Check":
    st.title("🔍 Domain Status Check")
    domain = st.text_input("Domain:", placeholder="example.com")
    if st.button("🔍 Check", type="primary"):
        if domain:
            st.info(f"Checking {domain}...")
            st.success("Feature requires DNS libraries. Install: dns.resolver, whois")

elif tool == "🔎 DNS Analyzer":
    st.title("🔎 DNS Analyzer")
    domain = st.text_input("Domain:", placeholder="example.com")
    if st.button("🔍 Analyze", type="primary"):
        if domain:
            st.info(f"Analyzing DNS for {domain}...")
            st.success("Feature requires DNS libraries")

elif tool == "🔍 NS Authority Checker":
    st.title("🔍 NS Authority Checker")
    st.markdown("Format: domain, ns1, ns2")
    input_text = st.text_area("Input:", placeholder="example.com, ns1.example.com, ns2.example.com")
    if st.button("🔍 Check", type="primary"):
        if input_text:
            lines = [l.strip() for l in input_text.split('\n') if l.strip()]
            for line in lines:
                parts = [p.strip() for p in line.split(',')]
                if len(parts) >= 2:
                    st.info(f"Checking: {parts[0]} with {parts[1:]}")

elif tool == "📊 WHOIS Lookup":
    st.title("📊 WHOIS Lookup")
    domain = st.text_input("Domain:", placeholder="example.com")
    if st.button("🔍 Lookup", type="primary"):
        if domain:
            st.info(f"Looking up {domain}...")
            st.success("Feature requires whois library")

elif tool == "📮 MX Record Checker":
    st.title("📮 MX Record Checker")
    domain = st.text_input("Domain:", placeholder="example.com")
    if st.button("🔍 Check MX", type="primary"):
        if domain:
            st.info(f"Checking MX for {domain}...")
            st.success("Feature requires DNS library")

elif tool == "✉️ Email Account Tester":
    st.title("✉️ Email Account Tester")
    st.warning("⚠️ Security: Never store credentials")
    col1, col2 = st.columns(2)
    with col1:
        email = st.text_input("Email:")
        imap_server = st.text_input("IMAP Server:")
    with col2:
        password = st.text_input("Password:", type="password")
        smtp_server = st.text_input("SMTP Server:")
    if st.button("🧪 Test", type="primary"):
        st.info("Feature requires imaplib/smtplib")

elif tool == "🔐 SPF/DKIM Check":
    st.title("🔐 SPF/DKIM/DMARC Check")
    domain = st.text_input("Domain:", placeholder="example.com")
    if st.button("🔍 Check", type="primary"):
        if domain:
            st.info(f"Checking email auth for {domain}...")
            st.success("Feature requires DNS library")

elif tool == "📄 Email Header Analyzer":
    st.title("📄 Email Header Analyzer")
    headers = st.text_area("Paste Headers:", height=300)
    if st.button("🔍 Analyze", type="primary"):
        if headers:
            lines = headers.split('\n')
            st.success(f"Parsed {len(lines)} header lines")
            for line in lines[:10]:
                if ':' in line:
                    key, val = line.split(':', 1)
                    st.code(f"{key}: {val.strip()}")

elif tool == "🔧 Web Error Troubleshooting":
    st.title("🔧 Web Error Troubleshooting")
    error = st.selectbox("Error:", [
        "500 Internal Server Error",
        "503 Service Unavailable",
        "404 Not Found",
        "403 Forbidden",
        "502 Bad Gateway"
    ])
    if error == "500 Internal Server Error":
        st.markdown("""
        ### 500 Internal Server Error
        **Causes:**
        - PHP errors
        - .htaccess issues
        - File permissions (should be 644/755)
        - Memory limit
        
        **Fixes:**
        1. Check error logs
        2. Rename .htaccess
        3. Check permissions
        4. Increase PHP memory
        """)

elif tool == "🔒 SSL Certificate Checker":
    st.title("🔒 SSL Certificate Checker")
    domain = st.text_input("Domain:", placeholder="example.com")
    if st.button("🔍 Check SSL", type="primary"):
        if domain:
            try:
                import ssl, socket
                context = ssl.create_default_context()
                with socket.create_connection((domain, 443), timeout=10) as sock:
                    with context.wrap_socket(sock, server_hostname=domain) as ssock:
                        cert = ssock.getpeercert()
                        st.success("✅ SSL Certificate found")
                        st.json(cert)
            except Exception as e:
                st.error(f"Error: {e}")

elif tool == "🔀 HTTPS Redirect Test":
    st.title("🔀 HTTPS Redirect Test")
    domain = st.text_input("Domain:", placeholder="example.com")
    if st.button("🔍 Test", type="primary"):
        if domain:
            try:
                resp = requests.get(f"http://{domain}", allow_redirects=True, timeout=10)
                if resp.url.startswith('https://'):
                    st.success("✅ HTTP redirects to HTTPS")
                else:
                    st.error("❌ No HTTPS redirect")
                st.info(f"Final URL: {resp.url}")
            except Exception as e:
                st.error(f"Error: {e}")

elif tool == "⚠️ Mixed Content Detector":
    st.title("⚠️ Mixed Content Detector")
    url = st.text_input("URL:", placeholder="https://example.com")
    if st.button("🔍 Scan", type="primary"):
        if url:
            try:
                resp = requests.get(url, timeout=15)
                http_count = resp.text.count('http://')
                if http_count > 0:
                    st.warning(f"⚠️ Found {http_count} HTTP resources")
                else:
                    st.success("✅ No mixed content")
            except Exception as e:
                st.error(f"Error: {e}")

elif tool == "📊 HTTP Status Code Checker":
    st.title("📊 HTTP Status Checker")
    url = st.text_input("URL:", placeholder="https://example.com")
    if st.button("🔍 Check", type="primary"):
        if url:
            try:
                resp = requests.head(url, allow_redirects=True, timeout=10)
                st.success(f"✅ Status: {resp.status_code} {resp.reason}")
            except Exception as e:
                st.error(f"Error: {e}")

elif tool == "🔗 Redirect Checker":
    st.title("🔗 Redirect Checker")
    url = st.text_input("URL:", placeholder="https://example.com")
    if st.button("🔍 Check", type="primary"):
        if url:
            try:
                resp = requests.get(url, allow_redirects=True, timeout=10)
                if resp.history:
                    st.success(f"✅ {len(resp.history)} redirect(s)")
                    for i, r in enumerate(resp.history, 1):
                        st.info(f"{i}. {r.url} → {r.status_code}")
                else:
                    st.info("No redirects")
            except Exception as e:
                st.error(f"Error: {e}")

elif tool == "🤖 robots.txt Viewer":
    st.title("🤖 robots.txt Viewer")
    domain = st.text_input("Domain:", placeholder="example.com")
    if st.button("🔍 Fetch", type="primary"):
        if domain:
            try:
                url = f"https://{domain}/robots.txt"
                resp = requests.get(url, timeout=10)
                if resp.status_code == 200:
                    st.success("✅ robots.txt found")
                    st.code(resp.text)
                else:
                    st.warning("⚠️ robots.txt not found")
            except Exception as e:
                st.error(f"Error: {e}")

elif tool == "⚡ Website Speed Test":
    st.title("⚡ Website Speed Test")
    url = st.text_input("URL:", placeholder="https://example.com")
    if st.button("⚡ Test", type="primary"):
        if url:
            try:
                start = time.time()
                resp = requests.get(url, timeout=30)
                load_time = time.time() - start
                
                col1, col2 = st.columns(2)
                with col1:
                    st.metric("Load Time", f"{load_time:.2f}s")
                with col2:
                    st.metric("Size", f"{len(resp.content)/1024:.2f} KB")
                
                if load_time < 3:
                    st.success("✅ Fast")
                else:
                    st.warning("⚠️ Could be faster")
            except Exception as e:
                st.error(f"Error: {e}")

elif tool == "🌐 My IP Address":
    st.title("🌐 My IP Address")
    ip = get_client_ip()
    st.markdown(f'<div class="success-box"><h2>{ip}</h2></div>', unsafe_allow_html=True)

elif tool == "📡 Ping Tool":
    st.title("📡 Ping Tool")
    hostname = st.text_input("Hostname:", placeholder="example.com")
    count = st.slider("Pings:", 1, 10, 4)
    if st.button("📡 Ping", type="primary"):
        if hostname:
            param = '-n' if platform.system().lower() == 'windows' else '-c'
            try:
                result = subprocess.run(['ping', param, str(count), hostname], 
                                      capture_output=True, text=True, timeout=30)
                st.code(result.stdout)
            except Exception as e:
                st.error(f"Error: {e}")

elif tool == "🔌 Port Checker":
    st.title("🔌 Port Checker")
    col1, col2 = st.columns(2)
    with col1:
        host = st.text_input("Host:", placeholder="example.com")
    with col2:
        port = st.number_input("Port:", min_value=1, max_value=65535, value=80)
    
    if st.button("🔌 Check", type="primary"):
        if host:
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(5)
                result = sock.connect_ex((host, int(port)))
                sock.close()
                if result == 0:
                    st.success(f"✅ Port {port} is OPEN")
                else:
                    st.error(f"❌ Port {port} is CLOSED")
            except Exception as e:
                st.error(f"Error: {e}")

elif tool == "🗺️ Traceroute":
    st.title("🗺️ Traceroute")
    hostname = st.text_input("Hostname:", placeholder="example.com")
    if st.button("🗺️ Trace", type="primary"):
        if hostname:
            st.info("Traceroute may take a minute...")
            try:
                if platform.system().lower() == 'windows':
                    cmd = ['tracert', '-d', '-w', '1000', hostname]
                else:
                    cmd = ['traceroute', '-m', '15', '-w', '2', hostname]
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
                st.code(result.stdout)
            except Exception as e:
                st.error(f"Error: {e}")

elif tool == "🗄️ MySQL Connection Tester":
    st.title("🗄️ MySQL Connection Tester")
    st.warning("⚠️ Never store credentials")
    col1, col2 = st.columns(2)
    with col1:
        host = st.text_input("Host:", placeholder="localhost")
        db = st.text_input("Database:")
    with col2:
        user = st.text_input("User:")
        pwd = st.text_input("Password:", type="password")
    if st.button("🧪 Test", type="primary"):
        st.info("Feature requires pymysql library")

elif tool == "📊 Database Size Calculator":
    st.title("📊 Database Size Calculator")
    st.code("""SELECT table_schema AS 'Database',
ROUND(SUM(data_length + index_length) / 1024 / 1024, 2) AS 'Size (MB)'
FROM information_schema.TABLES
GROUP BY table_schema;""")
    
    size = st.number_input("Size:", value=1024.0)
    unit = st.selectbox("Unit:", ["Bytes", "KB", "MB", "GB", "TB"])
    
    multipliers = {"Bytes": 1, "KB": 1024, "MB": 1024**2, "GB": 1024**3, "TB": 1024**4}
    size_bytes = size * multipliers[unit]
    
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Bytes", f"{size_bytes:,.0f}")
        st.metric("MB", f"{size_bytes/(1024**2):,.2f}")
    with col2:
        st.metric("GB", f"{size_bytes/(1024**3):,.4f}")
        st.metric("TB", f"{size_bytes/(1024**4):,.6f}")

elif tool == "📁 FTP Connection Tester":
    st.title("📁 FTP Connection Tester")
    st.warning("⚠️ Never store credentials")
    col1, col2 = st.columns(2)
    with col1:
        ftp_host = st.text_input("Host:")
        ftp_user = st.text_input("User:")
    with col2:
        ftp_pass = st.text_input("Password:", type="password")
        ftp_port = st.number_input("Port:", value=21)
    if st.button("🧪 Test", type="primary"):
        st.info("Feature requires ftplib library")

elif tool == "🔐 File Permission Checker":
    st.title("🔐 File Permission Checker")
    st.markdown("""
    **Recommended:**
    - Files: 644
    - Folders: 755
    - Sensitive: 600
    """)
    
    numeric = st.text_input("Numeric (e.g., 644):", max_chars=3)
    if numeric and len(numeric) == 3:
        try:
            def num_to_perm(n):
                n = int(n)
                return ('r' if n & 4 else '-') + ('w' if n & 2 else '-') + ('x' if n & 1 else '-')
            
            symbolic = num_to_perm(numeric[0]) + num_to_perm(numeric[1]) + num_to_perm(numeric[2])
            st.success(f"**Symbolic:** {symbolic}")
        except:
            st.error("Invalid format")

elif tool == "📚 Help Center":
    st.title("📚 Help Center")
    search = st.text_input("Search:", placeholder="email setup, dns, cpanel")
    if search:
        st.success("Search feature")
    st.markdown("### 📂 Categories")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.button("📧 Email")
    with col2:
        st.button("🌐 Domains")
    with col3:
        st.button("🗄️ Databases")

elif tool == "🔑 Password Strength Meter":
    st.title("🔑 Password Strength Meter")
    st.warning("⚠️ Checked locally, not sent anywhere")
    password = st.text_input("Password:", type="password")
    if password:
        strength, score, feedback, color = check_password_strength(password)
        st.markdown(f"### Strength: {strength}")
        st.progress(score / 6)
        if feedback:
            for tip in feedback:
                st.info(f"• {tip}")
        
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Length", len(password))
            st.metric("Lowercase", "✅" if re.search(r'[a-z]', password) else "❌")
        with col2:
            st.metric("Uppercase", "✅" if re.search(r'[A-Z]', password) else "❌")
            st.metric("Numbers", "✅" if re.search(r'\d', password) else "❌")
    
    st.markdown("---")
    length = st.slider("Generate Length:", 8, 32, 16)
    if st.button("🎲 Generate"):
        import string
        chars = string.ascii_letters + string.digits + string.punctuation
        generated = ''.join(random.choice(chars) for _ in range(length))
        st.code(generated)

elif tool == "🌍 Timezone Converter":
    st.title("🌍 Timezone Converter")
    st.info("Feature requires pytz library")
    
    from_time = st.time_input("Time:")
    offset = st.number_input("UTC Offset:", value=0)
    if from_time:
        from datetime import datetime, timedelta
        utc_dt = datetime.combine(datetime.today(), from_time)
        converted = utc_dt + timedelta(hours=offset)
        st.success(f"Converted: {converted.strftime('%H:%M:%S')}")

elif tool == "📋 Copy-Paste Utilities":
    st.title("📋 Copy-Paste Utilities")
    tab1, tab2 = st.tabs(["Case Converter", "Line Tools"])
    
    with tab1:
        text = st.text_area("Text:", height=150)
        if text:
            col1, col2 = st.columns(2)
            with col1:
                st.markdown("**UPPERCASE**")
                st.code(text.upper())
            with col2:
                st.markdown("**lowercase**")
                st.code(text.lower())
    
    with tab2:
        lines = st.text_area("Lines:", height=150)
        if lines:
            line_list = [l.strip() for l in lines.split('\n') if l.strip()]
            if st.button("Remove Duplicates"):
                unique = list(dict.fromkeys(line_list))
                st.code('\n'.join(unique))

elif tool == "📸 Screenshot Annotator":
    st.title("📸 Screenshot Annotator")
    uploaded = st.file_uploader("Upload:", type=['png', 'jpg', 'jpeg'])
    if uploaded:
        image = Image.open(uploaded)
        st.image(image, use_container_width=True)
        notes = st.text_area("Notes:", height=100)
        if notes:
            st.download_button("📥 Download Notes", notes, "notes.txt")

elif tool == "📝 Session Notes":
    st.title("📝 Session Notes")
    st.session_state.session_notes = st.text_area(
        "Notes:",
        value=st.session_state.session_notes,
        height=300
    )
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("💾 Save"):
            st.success("Saved")
    with col2:
        st.button("📋 Copy")
    with col3:
        if st.button("🗑️ Clear"):
            st.session_state.session_notes = ""
            st.rerun()
    
    if st.session_state.session_notes:
        st.download_button(
            "📥 Download",
            st.session_state.session_notes,
            f"notes_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        )

elif tool == "🗑️ Clear Cache Instructions":
    st.title("🗑️ Clear Cache Instructions")
    browser = st.selectbox("Browser:", ["Chrome", "Firefox", "Safari", "Edge"])
    st.markdown("---")
    if browser == "Chrome":
        st.markdown("""
        ### Google Chrome
        1. Press `Ctrl+Shift+Delete`
        2. Select "All time"
        3. Check "Cached images and files"
        4. Click "Clear data"
        
        **Hard Refresh:** `Ctrl+F5`
        """)
    elif browser == "Firefox":
        st.markdown("""
        ### Firefox
        1. Press `Ctrl+Shift+Delete`
        2. Select "Everything"
        3. Check "Cache"
        4. Click "Clear Now"
        """)

elif tool == "🧹 Flush DNS Cache":
    st.title("🧹 Flush DNS Cache")
    os_type = st.selectbox("OS:", ["Windows", "macOS", "Linux", "Google DNS"])
    st.markdown("---")
    if os_type == "Windows":
        st.markdown("### Windows")
        st.code("ipconfig /flushdns")
    elif os_type == "macOS":
        st.markdown("### macOS")
        st.code("sudo dscacheutil -flushcache; sudo killall -HUP mDNSResponder")
    elif os_type == "Linux":
        st.markdown("### Linux")
        st.code("sudo systemd-resolve --flush-caches")
    elif os_type == "Google DNS":
        domain = st.text_input("Domain:")
        if domain:
            st.link_button("🧹 Flush", f"https://dns.google/cache?q={domain}")

st.markdown("---")
st.markdown("<div style='text-align:center;padding:2rem;'><p>🔧 <strong>Support Buddy</strong> - Complete Support Toolkit</p></div>", unsafe_allow_html=True)
