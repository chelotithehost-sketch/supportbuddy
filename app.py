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
    page_title="Your Support Buddy",
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

import google.generativeai as genai
from google.api_core import exceptions
import time

# 1. Vision-capable models for ticket analysis
GEMINI_MODELS = ["gemini-2.5-flash", "gemini-2.5-flash-lite", "gemini-2.0-flash", "gemini-2.0-flash-lite-preview", "gemini-robotics-er-1.5-preview"]

def analyze_ticket_with_rotation(prompt, image_file):
    """
    Tries each model in GEMINI_MODELS until one succeeds or all fail.
    Replaces manual rate limit tracking.
    """
    for model_name in GEMINI_MODELS:
        try:
            # Initialize model
            model = genai.GenerativeModel(model_name)
            
            # Attempt analysis (passing both prompt and image)
            response = model.generate_content([prompt, image_file])
            
            # If successful, return the result and the model that worked
            return response.text, model_name

        except exceptions.ResourceExhausted:
            # This is the 'Rate Limit' error. If caught, we try the next model in the list.
            st.warning(f"⚠️ {model_name} rate limit reached. Switching to next model...")
            continue 

        except Exception as e:
            # Handle other errors (like invalid API key or network issues)
            st.error(f"❌ Error with {model_name}: {str(e)}")
            continue

    return None, None
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
    'cPanel Hosting Guide': [
        {'title': 'cPanel Hosting Guide', 'url': 'https://help.hostafrica.com/category/control-panel-and-emails/cpanel',
         'keywords': ['cpanel', 'hosting', 'login', 'access', 'recaptcha', 'captcha']},
    ],
    'DirectAdmin Hosting Guide': [
        {'title': 'Email cPanel', 'url': 'https://help.hostafrica.com/category/control-panel-and-emails/directadmin',
         'keywords': ['DirectAdmin', 'hosting', 'login', 'access', 'recaptcha', 'captcha']},
    ],
    'cPanel-email': [
        {'title': 'Email cPanel', 'url': 'https://help.hostafrica.com/category/control-panel-and-emails/cpanel',
         'keywords': ['email', 'mail', 'smtp', 'imap', 'pop3']},
    ],
    'DirectAdmin-email': [
        {'title': 'Email DirectAdmin', 'url': 'https://help.hostafrica.com/category/control-panel-and-emails/directadmin',
         'keywords': ['email', 'mail', 'smtp', 'imap', 'pop3']},
    ],
    'HMail-Email': [
        {'title': 'Email Configuration', 'url': 'https://help.hostafrica.com/category/professional-email-and-workspace',
         'keywords': ['email', 'mail', 'smtp', 'imap', 'pop3']},
    ],
    'domain': [
        {'title': 'Domain Management', 'url': 'https://help.hostafrica.com/category/domains',
         'keywords': ['domain', 'nameserver', 'dns', 'transfer']},
    ],
    'Backup': [
        {'title': 'JetBackup', 'url': 'https://help.hostafrica.com/category/jetbackup-5',
         'keywords': ['Backup', 'JetBackup']},
    ],
    'Self Managed VPS': [
        {'title': 'Self Managed VPS', 'url': 'https://help.hostafrica.com/category/vps',
         'keywords': ['VPS', 'Cloud Servers', 'Self Managed VPS']},
    ],
    'Basekit Site Builder': [
        {'title': 'Website Builder Basekit', 'url': 'https://www.guides.business/hc/en-gb/articles/19964374415389-Sitebuilder-FAQs',
         'keywords': ['SiteBuilder', 'Basekit']},
    ],
    'VPS Application Topics': [
        {'title': 'Website Builder Basekit', 'url': 'https://help.hostafrica.com/category/vps-applications-topics',
         'keywords': ['N8N', 'SupaBase']},
    ],
    'General Topics': [
        {'title': 'HostAfrica General Topics', 'url': 'https://help.hostafrica.com/category/hostafrica-general',
         'keywords': ['Support PIN', 'Client Area']},
    ],
    'ssl': [
        {'title': 'SSL Certificates', 'url': 'https://help.hostafrica.com/category/ssl-certificates',
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

def analyze_ticket_with_rotation(prompt, image_data):
    """Try models in rotation until one succeeds"""
    for model_name in GEMINI_MODELS:
        try:
            import google.generativeai as genai
            model = genai.GenerativeModel(model_name)
            
            content = [prompt, {"mime_type": "image/jpeg", "data": image_data}] if image_data else prompt
            response = model.generate_content(content)
            
            return response.text, model_name
            
        except Exception as e:
            error_str = str(e)
            if "429" in error_str or "ResourceExhausted" in error_str or "rate" in error_str.lower():
                continue
            else:
                st.warning(f"Model {model_name} error: {error_str[:50]}")
                continue
    
    return None, None

def analyze_ticket_with_ai(ticket_text, image_data=None):
    """Analyze ticket with AI (with optional image)"""
    if not GEMINI_API_KEY:
        return analyze_ticket_keywords(ticket_text)
    
    try:
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

        result_text, model_used = analyze_ticket_with_rotation(prompt, image_data)
        
        if result_text:
            text = result_text.strip().replace("```json", "").replace("```", "").strip()
            result = json.loads(text)
            result['kb_articles'] = search_kb_articles(ticket_text)
            if model_used:
                st.caption(f"💡 Analyzed using: {model_used}")
            return result
        else:
            st.warning("⚠️ All AI models busy, using keyword analysis")
            return analyze_ticket_keywords(ticket_text)
        
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
    ### Quick Start (60s)
    1. ✅ Check priority (VIP?)
    2. ✅ Verify identity (PIN)
    3. ✅ Check service status
    4. ✅ Add tags
    
    ### Service Health
    - Domain: Active? Expired?
    - Hosting: Active/Suspended?
    - NS: ns1-4.host-ww.net
    - DA NS: dan1-2.host-ww.net
    
    ### Troubleshooting
    **Email**: MX/SPF/DKIM/DMARC
    **Website**: A record, NS, logs
    **cPanel/ DirectAdmin**: IP blocks, login attempts
    **SSL**: Certificate, mixed content
    **Others**: Basekit Sitebuilder, HMailPlus
    
    ### Tags
    Mail | Hosting | DNS | SiteBuilder| VPS
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
    st.header("🌐 Comprehensive WHOIS Lookup")
    st.markdown("Check domain registration, expiration, status, and registrar information")
    
    domain = st.text_input("Enter domain name:", placeholder="example.com", key="whois_domain")
    
    if st.button("🔍 Check WHOIS", use_container_width=True):
        if domain:
            domain = domain.strip().lower()
            
            with st.spinner(f"Performing WHOIS lookup for {domain}..."):
                issues = []
                warnings = []
                success_checks = []
                
                st.subheader("📝 Domain Registration Information")
                
                try:
                    w = whois.whois(domain)
                    
                    if w and w.domain_name:
                        st.success("✅ WHOIS information retrieved successfully")
                        success_checks.append("WHOIS lookup successful")
                        
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            st.markdown("### Basic Information")
                            st.write(f"**Domain:** {domain}")
                            
                            if w.registrar:
                                st.write(f"**Registrar:** {w.registrar}")
                            
                            if w.registrant:
                                registrant = str(w.registrant)
                                if 'redacted' not in registrant.lower():
                                    st.write(f"**Registrant:** {registrant}")
                            
                            # Status
                            if w.status:
                                st.markdown("### Domain Status")
                                status_list = w.status if isinstance(w.status, list) else [w.status]
                                
                                for status in status_list[:5]:
                                    status_str = str(status)
                                    status_lower = status_str.lower()
                                    
                                    if any(x in status_lower for x in ['ok', 'active', 'registered']):
                                        st.success(f"✅ {status_str.split()[0]}")
                                        success_checks.append("Domain status: OK")
                                    elif any(x in status_lower for x in ['hold', 'lock', 'suspended', 'pending delete']):
                                        st.error(f"❌ {status_str.split()[0]}")
                                        issues.append(f"Domain status issue: {status_str.split()[0]}")
                                    elif any(x in status_lower for x in ['pending', 'verification', 'grace']):
                                        st.warning(f"⚠️ {status_str.split()[0]}")
                                        warnings.append(f"Domain status: {status_str.split()[0]}")
                                    elif 'expired' in status_lower:
                                        st.error(f"❌ {status_str.split()[0]}")
                                        issues.append("Domain expired")
                                    else:
                                        st.info(f"ℹ️ {status_str.split()[0]}")
                        
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

elif tool == "IP":
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

elif tool == "cPanel":
    st.header("📂 cPanel List")
    col1, col2 = st.columns([3, 1])
    with col1:
        st.info("View cPanel accounts")
    with col2:
        st.link_button("Open", "https://my.hostafrica.com/admin/custom/scripts/custom_tests/listaccounts.php", use_container_width=True)

elif tool == "cPanel":
    st.header("📂 cPanel Account List")
    st.markdown("View all cPanel hosting accounts and their details")
    col1, col2 = st.columns([3, 1])
    with col1:
        st.info("Access the complete list of cPanel accounts")
    with col2:
        st.link_button("📂 Open List", "https://my.hostafrica.com/admin/custom/scripts/custom_tests/listaccounts.php", use_container_width=True)

elif tool == "MyIP":
    st.header("📍 Find My IP Address")
    st.markdown("Quickly discover your current public IP address")
    col1, col2 = st.columns([3, 1])
    with col1:
        st.info("Click to open HostAfrica's IP detection tool")
    with col2:
        st.link_button("🔍 Get My IP", "https://ip.hostafrica.com/", use_container_width=True)

elif tool == "NS":
    st.header("🔄 Bulk Nameserver Updater")
    st.markdown("Update nameservers for multiple domains at once")
    col1, col2 = st.columns([3, 1])
    with col1:
        st.info("Use this tool to bulk update nameservers in WHMCS")
    with col2:
        st.link_button("🔄 Open Updater", "https://my.hostafrica.com/admin/addonmodules.php?module=nameserv_changer", use_container_width=True)

elif tool == "SSL":
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

elif tool == "Help":
    st.header("📚 HostAfrica Help Center")
    st.markdown("Search the knowledge base for guides and documentation")
    col1, col2 = st.columns([3, 1])
    with col1:
        st.info("Access the complete HostAfrica help center and documentation")
    with col2:
        st.link_button("📚 Open Help", "https://help.hostafrica.com", use_container_width=True)

elif tool == "Flush":
    st.header("🧹 Flush Google DNS Cache")
    st.markdown("Clear Google's DNS cache for a domain to force fresh lookups")
    col1, col2 = st.columns([3, 1])
    with col1:
        st.info("Use this to force Google DNS to fetch fresh DNS records for a domain")
    with col2:
        st.link_button("🧹 Flush Cache", "https://dns.google/cache", use_container_width=True)
