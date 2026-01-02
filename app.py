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

# Page Configuration
st.set_page_config(
    page_title="Tech Support Toolkit",
    page_icon="🔧",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Configure Gemini API
GEMINI_API_KEY = ""
try:
    GEMINI_API_KEY = st.secrets.get("GEMINI_API_KEY", "")
    if GEMINI_API_KEY:
        import google.generativeai as genai
        genai.configure(api_key=GEMINI_API_KEY)
except:
    pass

# Gemini models
GEMINI_MODELS = ["gemini-2.5-flash", "gemini-2.5-flash-lite"]

# Rate limit tracking
if 'api_calls' not in st.session_state:
    st.session_state.api_calls = []

def check_rate_limit():
    """Check if we're within rate limits"""
    now = time.time()
    st.session_state.api_calls = [t for t in st.session_state.api_calls if now - t < 60]
    if len(st.session_state.api_calls) >= 2:
        return False, 60 - (now - st.session_state.api_calls[0])
    return True, 0

def record_api_call():
    """Record an API call"""
    st.session_state.api_calls.append(time.time())

# Custom CSS
st.markdown("""
<style>
    .stButton > button {
        width: 100%;
        background-color: #4A9B8E;
        color: white;
        border: none;
        padding: 0.4rem 0.6rem;
        font-weight: 500;
        font-size: 0.85rem;
        border-radius: 6px;
        height: 42px;
    }
    .stButton > button:hover {
        background-color: #3A8B7E;
    }
    .stMarkdown a {
        color: #4A9B8E !important;
        font-weight: 600;
    }
    [data-testid="stMetricValue"] {
        font-size: 1.2rem;
    }
</style>
""", unsafe_allow_html=True)

# KB Database
HOSTAFRICA_KB = {
    'hosting': [
        {'title': 'cPanel Hosting Guide', 'url': 'https://help.hostafrica.com/en/category/web-hosting-b01r28/',
         'keywords': ['cpanel', 'hosting', 'login', 'access', 'recaptcha', 'captcha']},
    ],
    'email': [
        {'title': 'Email Configuration', 'url': 'https://help.hostafrica.com/en/category/email-1fmw9ki/',
         'keywords': ['email', 'mail', 'smtp', 'imap', 'pop3']},
    ],
    'domain': [
        {'title': 'Domain Management', 'url': 'https://help.hostafrica.com/en/category/domains-1yz6z58/',
         'keywords': ['domain', 'nameserver', 'dns', 'transfer']},
    ],
    'ssl': [
        {'title': 'SSL Certificates', 'url': 'https://help.hostafrica.com/en/category/ssl-certificates-1n94vbj/',
         'keywords': ['ssl', 'https', 'certificate', 'secure']},
    ],
}

def search_kb_articles(keywords):
    """Search KB for relevant articles"""
    articles = []
    keywords_lower = keywords.lower()
    for category, items in HOSTAFRICA_KB.items():
        for item in items:
            if any(k in keywords_lower for k in item['keywords']):
                if item not in articles:
                    articles.append(item)
    return articles[:3]

def image_to_base64(image_file):
    """Convert uploaded image to base64"""
    try:
        image = Image.open(image_file)
        max_size = 1024
        if max(image.size) > max_size:
            image.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)
        
        if image.mode in ('RGBA', 'LA', 'P'):
            background = Image.new('RGB', image.size, (255, 255, 255))
            background.paste(image, mask=image.split()[-1] if image.mode == 'RGBA' else None)
            image = background
        
        buffer = io.BytesIO()
        image.save(buffer, format='JPEG', quality=85)
        return base64.b64encode(buffer.getvalue()).decode()
    except Exception as e:
        st.error(f"Error processing image: {str(e)}")
        return None

def analyze_ticket_with_ai(ticket_text, image_data=None):
    """Analyze ticket with AI (with optional image)"""
    if not GEMINI_API_KEY:
        return analyze_ticket_keywords(ticket_text)
    
    can_call, wait_time = check_rate_limit()
    if not can_call:
        st.warning(f"⏱️ Rate limit: Please wait {int(wait_time)} seconds")
        return analyze_ticket_keywords(ticket_text)
    
    try:
        import google.generativeai as genai
        model = genai.GenerativeModel(random.choice(GEMINI_MODELS))
        
        prompt = f"""Analyze this HostAfrica support ticket{"and screenshot" if image_data else ""}.

HostAfrica: web hosting (cPanel/DirectAdmin), domains, email, SSL, VPS
NS: cPanel (ns1-4.host-ww.net), DirectAdmin (dan1-2.host-ww.net)

Ticket: {ticket_text}

{"IMPORTANT: Analyze the screenshot for error messages, warnings, or visual clues." if image_data else ""}

JSON format:
{{
    "issue_type": "Specific issue",
    "checks": ["check1", "check2"],
    "actions": ["action1", "action2"],
    "response_template": "Professional response",
    "kb_topics": ["topic1"],
    "screenshot_analysis": "What the screenshot shows and how it helps diagnose"
}}"""

        content = [prompt, {"mime_type": "image/jpeg", "data": image_data}] if image_data else prompt
        
        response = model.generate_content(content)
        record_api_call()
        
        text = response.text.strip().replace("```json", "").replace("```", "").strip()
        result = json.loads(text)
        result['kb_articles'] = search_kb_articles(ticket_text)
        return result
        
    except Exception as e:
        st.warning(f"AI unavailable: {str(e)[:100]}")
        return analyze_ticket_keywords(ticket_text)

def analyze_ticket_keywords(ticket_text):
    """Keyword-based analysis"""
    ticket_lower = ticket_text.lower()
    result = {
        'issue_type': 'General Support',
        'checks': [],
        'actions': [],
        'response_template': '',
        'kb_articles': [],
        'screenshot_analysis': None
    }
    
    if any(w in ticket_lower for w in ['cpanel', 'login', 'recaptcha', 'captcha', 'access']):
        result['issue_type'] = '🔐 cPanel Access Issue'
        result['checks'] = ['Check if client IP is blocked', 'Verify hosting account is active', 'Check for failed login attempts']
        result['actions'] = ['Use IP Unban tool', 'Check client IP with IP Lookup', 'Clear browser cache']
        
        ip_match = re.search(r'IP Address:\s*(\d+\.\d+\.\d+\.\d+)', ticket_text)
        client_ip = ip_match.group(1) if ip_match else 'client IP'
        
        result['response_template'] = f"""Hi there,

Thank you for contacting HostAfrica Support regarding your cPanel login issue.

I can see you're having trouble with the reCAPTCHA verification. This is usually caused by IP address blocking.

**Your IP**: {client_ip}

**I've taken these steps:**
- Checked your account status: Active
- Reviewed IP blocks on the server
- Removed your IP from the block list

**Please try these steps:**
1. Clear your browser cache and cookies
2. Try accessing cPanel in incognito/private window
3. If issue persists, try a different browser
4. Wait 15-30 minutes after multiple failed attempts

For help: https://help.hostafrica.com/en/category/web-hosting-b01r28/

Best regards,
[Your Name]
HostAfrica Support Team"""
        result['kb_articles'] = search_kb_articles('cpanel login')
    
    elif any(w in ticket_lower for w in ['email', 'mail', 'smtp', 'imap']):
        result['issue_type'] = '📧 Email Issue'
        result['checks'] = ['Check MX records', 'Verify SPF/DKIM']
        result['actions'] = ['Use DNS tool', 'Check IP blocks']
        result['response_template'] = "Hi [Client],\n\nThank you for contacting HostAfrica about your email issue.\n\nI've checked:\n- MX records\n- Email authentication\n\n[Action taken]\n\nFor help: https://help.hostafrica.com/en/category/email-1fmw9ki/\n\nBest regards,\nHostAfrica Support"
        result['kb_articles'] = search_kb_articles('email')
    
    elif any(w in ticket_lower for w in ['website', 'site', '404', '500']):
        result['issue_type'] = '🌐 Website Issue'
        result['checks'] = ['Check A record', 'Verify nameservers']
        result['actions'] = ['Use DNS tool', 'Check WHOIS']
        result['response_template'] = "Hi [Client],\n\nI've investigated your website issue.\n\nStatus:\n- Domain: [Status]\n- DNS: [Status]\n\n[Action taken]\n\nFor help: https://help.hostafrica.com/en/category/web-hosting-b01r28/\n\nBest regards,\nHostAfrica Support"
        result['kb_articles'] = search_kb_articles('website')
    
    elif any(w in ticket_lower for w in ['ssl', 'https', 'certificate']):
        result['issue_type'] = '🔒 SSL Certificate Issue'
        result['checks'] = ['Check SSL certificate', 'Verify expiration']
        result['actions'] = ['Use SSL Check tool', 'Install Let\'s Encrypt']
        result['response_template'] = "Hi [Client],\n\nI've reviewed your SSL certificate.\n\nStatus:\n- Certificate: [Status]\n- Expiration: [Date]\n\n[Action taken]\n\nFor help: https://help.hostafrica.com/en/category/ssl-certificates-1n94vbj/\n\nBest regards,\nHostAfrica Support"
        result['kb_articles'] = search_kb_articles('ssl')
    
    else:
        result['checks'] = ['Verify identity', 'Check service status']
        result['actions'] = ['Request more details']
        result['response_template'] = "Hi [Client],\n\nThank you for contacting HostAfrica Support.\n\nTo assist better, I need more information:\n[Questions]\n\nVisit: https://help.hostafrica.com/\n\nBest regards,\nHostAfrica Support"
    
    return result

# SIDEBAR
st.sidebar.title("🎫 Ticket Analyzer")

with st.sidebar.expander("🤖 AI Analysis + Screenshots", expanded=False):
    st.markdown("""
    **AI can analyze:**
    - 📝 Ticket text
    - 📷 Error screenshots
    - 🔐 Browser warnings
    - 🔒 SSL errors
    - 🖥️ cPanel issues
    """)
    
    ticket_thread = st.text_area(
        "Ticket conversation:",
        height=150,
        placeholder="Paste ticket thread here...",
        key="ticket_input"
    )
    
    uploaded_image = st.file_uploader(
        "📎 Upload Screenshot (optional)",
        type=['png', 'jpg', 'jpeg', 'gif'],
        help="Upload error screenshots or interface issues",
        key="ticket_image"
    )
    
    if uploaded_image:
        st.image(uploaded_image, caption="Uploaded Screenshot", use_container_width=True)
        st.caption("✅ Screenshot will be analyzed")
    
    can_call, wait_time = check_rate_limit()
    if not can_call:
        st.warning(f"⏱️ Wait {int(wait_time)}s")
    else:
        remaining = 2 - len(st.session_state.api_calls)
        st.caption(f"✅ API calls: {remaining}/2 per minute")
    
    if st.button("🔍 Analyze Ticket", key="analyze_btn", use_container_width=True):
        if ticket_thread:
            with st.spinner("Analyzing" + (" with screenshot" if uploaded_image else "") + "..."):
                image_base64 = None
                if uploaded_image and GEMINI_API_KEY:
                    image_base64 = image_to_base64(uploaded_image)
                    if not image_base64:
                        st.warning("⚠️ Image failed, analyzing text only")
                
                analysis = analyze_ticket_with_ai(ticket_thread, image_base64)
                
                if analysis:
                    st.success("✅ Analysis Complete")
                    
                    st.markdown("**Issue Type:**")
                    st.info(analysis.get('issue_type', 'General'))
                    
                    if analysis.get('screenshot_analysis'):
                        st.markdown("**📷 Screenshot Analysis:**")
                        st.info(analysis['screenshot_analysis'])
                    
                    kb = analysis.get('kb_articles', [])
                    if kb:
                        st.markdown("**📚 KB Articles:**")
                        for a in kb:
                            st.markdown(f"- [{a['title']}]({a['url']})")
                    
                    st.markdown("**Checks:**")
                    for c in analysis.get('checks', []):
                        st.markdown(f"- {c}")
                    
                    st.markdown("**Actions:**")
                    for a in analysis.get('actions', []):
                        st.markdown(f"- {a}")
                    
                    with st.expander("📝 Response Template"):
                        resp = analysis.get('response_template', '')
                        st.text_area("Copy:", value=resp, height=300, key="resp")
        else:
            st.warning("Paste ticket first")

st.sidebar.divider()

with st.sidebar.expander("📋 Support Checklist", expanded=True):
    st.markdown("""
    ### Quick Start
    1. ✅ Check priority
    2. ✅ Verify identity (PIN)
    3. ✅ Check service status
    4. ✅ Add tags
    
    ### Service Health
    - Domain: Active?
    - Hosting: Active/Suspended?
    - NS: ns1-4.host-ww.net
    
    ### Troubleshooting
    **Email**: MX/SPF/DKIM
    **Website**: A record, NS
    **cPanel**: IP blocks
    **SSL**: Certificate, mixed content
    
    ### Tags
    Mail | Hosting | DNS | Billing | VPS
    """)

st.sidebar.divider()
st.sidebar.caption("💡 HostAfrica Toolkit v2.1")
st.sidebar.caption("🖼️ Now with screenshot analysis!")

# MAIN APP
st.title("🔧 Tech Support Toolkit")

st.markdown("### Quick Tools")
col1, col2, col3, col4, col5, col6 = st.columns(6)

with col1:
    if st.button("🔑 PIN", use_container_width=True):
        st.session_state.tool = "PIN"
with col2:
    if st.button("🔓 Unban", use_container_width=True):
        st.session_state.tool = "Unban"
with col3:
    if st.button("🗂️ DNS", use_container_width=True):
        st.session_state.tool = "DNS"
with col4:
    if st.button("🌐 WHOIS", use_container_width=True):
        st.session_state.tool = "WHOIS"
with col5:
    if st.button("🔍 IP", use_container_width=True):
        st.session_state.tool = "IP"
with col6:
    if st.button("📂 cPanel", use_container_width=True):
        st.session_state.tool = "cPanel"

col7, col8, col9, col10, col11, col12 = st.columns(6)
with col7:
    if st.button("📍 My IP", use_container_width=True):
        st.session_state.tool = "MyIP"
with col8:
    if st.button("🔄 NS", use_container_width=True):
        st.session_state.tool = "NS"
with col9:
    if st.button("🔒 SSL", use_container_width=True):
        st.session_state.tool = "SSL"
with col10:
    if st.button("📚 Help", use_container_width=True):
        st.session_state.tool = "Help"
with col11:
    if st.button("🧹 Flush", use_container_width=True):
        st.session_state.tool = "Flush"
with col12:
    st.write("")

st.divider()

if 'tool' not in st.session_state:
    st.session_state.tool = "DNS"

tool = st.session_state.tool

# TOOLS
if tool == "PIN":
    st.header("🔐 PIN Checker")
    col1, col2 = st.columns([3, 1])
    with col1:
        st.info("Verify client PIN")
    with col2:
        st.link_button("Open", "https://my.hostafrica.com/admin/admin_tool/client-pin", use_container_width=True)

elif tool == "Unban":
    st.header("🔓 IP Unban")
    col1, col2 = st.columns([3, 1])
    with col1:
        st.info("Remove IP blocks")
    with col2:
        st.link_button("Open", "https://my.hostafrica.com/admin/custom/scripts/unban/", use_container_width=True)

elif tool == "DNS":
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

elif tool == "WHOIS":
    st.header("🌐 WHOIS Lookup")
    domain = st.text_input("Enter domain:", placeholder="example.com")
    
    if st.button("🔍 Check WHOIS", use_container_width=True):
        if domain:
            with st.spinner("Checking WHOIS..."):
                try:
                    w = whois.whois(domain.strip().lower())
                    if w and w.domain_name:
                        st.success("✅ WHOIS retrieved")
                        
                        col1, col2 = st.columns(2)
                        with col1:
                            st.write(f"**Domain:** {domain}")
                            if w.registrar:
                                st.write(f"**Registrar:** {w.registrar}")
                        
                        with col2:
                            if w.expiration_date:
                                exp = w.expiration_date[0] if isinstance(w.expiration_date, list) else w.expiration_date
                                st.write(f"**Expires:** {str(exp).split()[0]}")
                                days = (exp - datetime.now()).days
                                if days < 0:
                                    st.error(f"❌ Expired {abs(days)}d ago")
                                elif days < 30:
                                    st.error(f"⚠️ {days} days left")
                                else:
                                    st.success(f"✅ {days} days")
                        
                        if w.name_servers:
                            st.markdown("**Nameservers:**")
                            for ns in (w.name_servers[:4] if isinstance(w.name_servers, list) else [w.name_servers]):
                                st.code(f"• {str(ns).lower().rstrip('.')}")
                except:
                    st.error("❌ WHOIS failed")
                    st.info(f"Try: https://who.is/whois/{domain}")

elif tool == "IP":
    st.header("🔍 IP Lookup")
    ip = st.text_input("Enter IP:", placeholder="8.8.8.8")
    
    if st.button("🔍 Lookup", use_container_width=True):
        if ip:
            try:
                res = requests.get(f"http://ip-api.com/json/{ip}", timeout=5).json()
                if res.get('status') == 'success':
                    st.success(f"✅ Found: {ip}")
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("City", res.get('city', 'N/A'))
                    with col2:
                        st.metric("Country", res.get('country', 'N/A'))
                    with col3:
                        st.metric("ISP", res.get('isp', 'N/A')[:20])
            except:
                st.error("❌ Failed")

elif tool == "cPanel":
    st.header("📂 cPanel List")
    col1, col2 = st.columns([3, 1])
    with col1:
        st.info("View cPanel accounts")
    with col2:
        st.link_button("Open", "https://my.hostafrica.com/admin/custom/scripts/custom_tests/listaccounts.php", use_container_width=True)

elif tool == "MyIP":
    st.header("📍 My IP")
    col1, col2 = st.columns([3, 1])
    with col1:
        st.info("Find your IP")
    with col2:
        st.link_button("Open", "https://ip.hostafrica.com/", use_container_width=True)

elif tool == "NS":
    st.header("🔄 NS Updater")
    col1, col2 = st.columns([3, 1])
    with col1:
        st.info("Bulk update nameservers")
    with col2:
        st.link_button("Open", "https://my.hostafrica.com/admin/addonmodules.php?module=nameserv_changer", use_container_width=True)

elif tool == "SSL":
    st.header("🔒 SSL Check + Mixed Content")
    domain_ssl = st.text_input("Enter domain:", placeholder="example.com")
    
    if st.button("🔍 Check SSL", use_container_width=True):
        if domain_ssl:
            domain_ssl = domain_ssl.replace('https://', '').replace('http://', '').replace('www.', '').split('/')[0]
            
            with st.spinner("Checking SSL..."):
                try:
                    ctx = ssl.create_default_context()
                    with socket.create_connection((domain_ssl, 443), timeout=10) as sock:
                        with ctx.wrap_socket(sock, server_hostname=domain_ssl) as s:
                            cert = s.getpeercert()
                            st.success("✅ SSL valid")
                            
                            na = cert.get('notAfter')
                            if na:
                                exp = datetime.strptime(na, '%b %d %H:%M:%S %Y %Z')
                                days = (exp - datetime.now()).days
                                if days > 30:
                                    st.success(f"✅ {days} days remaining")
                                else:
                                    st.warning(f"⚠️ {days} days remaining")
                            
                            # Mixed Content Check
                            st.subheader("🔍 Mixed Content Check")
                            try:
                                response = requests.get(f"https://{domain_ssl}", timeout=10, verify=True)
                                http_resources = re.findall(r'http://[^"\'\s<>]+', response.text)
                                
                                if http_resources:
                                    st.warning(f"⚠️ Found {len(http_resources)} mixed content issue(s)")
                                    for resource in http_resources[:3]:
                                        st.code(resource)
                                    if len(http_resources) > 3:
                                        st.info(f"...and {len(http_resources) - 3} more")
                                else:
                                    st.success("✅ No mixed content issues!")
                            except:
                                st.warning("⚠️ Could not check mixed content")
                except:
                    st.error("❌ SSL check failed")

elif tool == "Help":
    st.header("📚 Help Center")
    col1, col2 = st.columns([3, 1])
    with col1:
        st.info("Search documentation")
    with col2:
        st.link_button("Open", "https://help.hostafrica.com", use_container_width=True)

elif tool == "Flush":
    st.header("🧹 Flush DNS")
    col1, col2 = st.columns([3, 1])
    with col1:
        st.info("Clear Google DNS cache")
    with col2:
        st.link_button("Open", "https://dns.google/cache", use_container_width=True)
