import streamlit as st
import requests
import time
import json
from datetime import datetime
import os
import base64
from typing import Dict, Any

# Configuration
BJJ_BACKEND_URL = os.getenv("BJJ_BACKEND_URL", "https://sam22ridhi-bjj-ai-backend.hf.space")

# Page configuration
st.set_page_config(
    page_title="BJJ AI Coach - Pro Analysis",
    page_icon="🥋",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Enhanced Custom CSS matching client's dark theme
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700;800&display=swap');
    
    html, body, [class*="css"] { 
        font-family: 'Inter', sans-serif;
        background-color: #0a0a0a;
    }
    
    .main-title {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-size: 3.5rem;
        font-weight: 800;
        text-align: center;
        margin-bottom: 0.5rem;
        letter-spacing: -1px;
    }
    
    .subtitle { 
        text-align: center; 
        color: #888; 
        font-size: 1.2rem; 
        margin-bottom: 2rem;
        font-weight: 300;
    }
    
    .overall-performance {
        background: linear-gradient(135deg, #1a1a1a 0%, #2d2d2d 100%);
        border-radius: 20px;
        padding: 40px;
        text-align: center;
        margin: 30px 0;
        border: 2px solid #333;
        box-shadow: 0 10px 40px rgba(0,0,0,0.5);
    }
    
    .performance-score {
        font-size: 5rem;
        font-weight: 800;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin: 20px 0;
    }
    
    .performance-label {
        color: #aaa;
        font-size: 1.5rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 2px;
        margin-top: 10px;
    }
    
    .grade-badge {
        display: inline-block;
        padding: 8px 20px;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        border-radius: 12px;
        color: white;
        font-weight: 700;
        font-size: 1.2rem;
        margin: 5px;
    }
    
    .skill-card {
        background: #1a1a1a;
        border-radius: 15px;
        padding: 25px;
        margin: 10px 0;
        border-left: 4px solid #667eea;
        box-shadow: 0 4px 15px rgba(0,0,0,0.3);
    }
    
    .skill-label {
        color: #aaa;
        font-size: 0.9rem;
        text-transform: uppercase;
        font-weight: 600;
        letter-spacing: 1px;
    }
    
    .skill-score {
        font-size: 2.5rem;
        font-weight: 800;
        color: white;
        margin: 10px 0;
    }
    
    .progress-bar-custom {
        background: #2a2a2a;
        border-radius: 10px;
        height: 12px;
        overflow: hidden;
        margin-top: 10px;
    }
    
    .progress-fill {
        height: 100%;
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        border-radius: 10px;
        transition: width 0.5s ease;
    }
    
    .strength-card {
        background: linear-gradient(135deg, #1a4d2e 0%, #1e5f3a 100%);
        border-radius: 12px;
        padding: 20px;
        margin: 10px 0;
        border-left: 4px solid #38ef7d;
    }
    
    .weakness-card {
        background: linear-gradient(135deg, #4d1a1a 0%, #5f1e1e 100%);
        border-radius: 12px;
        padding: 20px;
        margin: 10px 0;
        border-left: 4px solid #ff6a00;
    }
    
    .opportunity-card {
        background: #1a1a2e;
        border-radius: 12px;
        padding: 20px;
        margin: 10px 0;
        border-left: 4px solid #e94560;
    }
    
    .timestamp-badge {
        background: #667eea;
        color: white;
        padding: 4px 12px;
        border-radius: 8px;
        font-weight: 600;
        font-family: 'Courier New', monospace;
        font-size: 0.9rem;
    }
    
    .category-badge {
        background: #764ba2;
        color: white;
        padding: 4px 10px;
        border-radius: 6px;
        font-size: 0.75rem;
        font-weight: 600;
        text-transform: uppercase;
        margin-left: 10px;
    }
    
    .drill-card {
        background: linear-gradient(135deg, #1a1a2e 0%, #2d2d40 100%);
        border-radius: 12px;
        padding: 25px;
        margin: 15px 0;
        border: 2px solid #333;
    }
    
    .drill-header {
        color: #667eea;
        font-size: 1.3rem;
        font-weight: 700;
        margin-bottom: 10px;
    }
    
    .drill-meta {
        display: inline-block;
        background: #2a2a3e;
        padding: 6px 12px;
        border-radius: 8px;
        margin-right: 10px;
        font-size: 0.85rem;
        color: #aaa;
    }
    
    .coach-notes-section {
        background: linear-gradient(135deg, #1a1a1a 0%, #2d2d2d 100%);
        border-radius: 15px;
        padding: 30px;
        margin: 30px 0;
        border: 2px solid #667eea;
        box-shadow: 0 8px 30px rgba(102, 126, 234, 0.2);
    }
    
    .stButton>button {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border: none;
        border-radius: 25px;
        font-weight: 700;
        padding: 15px 40px;
        font-size: 1.1rem;
        transition: all 0.3s ease;
    }
    
    .stButton>button:hover {
        transform: translateY(-2px);
        box-shadow: 0 10px 25px rgba(102, 126, 234, 0.4);
    }
    
    .fallback-warning {
        background: linear-gradient(135deg, #4d3d1a 0%, #5f4a1e 100%);
        border-left: 4px solid #ffb800;
        padding: 20px;
        border-radius: 10px;
        margin: 20px 0;
    }
    </style>
""", unsafe_allow_html=True)

def check_backend_health(url: str) -> tuple[bool, str]:
    try:
        response = requests.get(f"{url}/", timeout=3)
        if response.status_code == 200:
            data = response.json()
            version = data.get("version", "Unknown")
            return True, f"Online v{version} ✅"
        return False, f"Status {response.status_code} ❌"
    except Exception as e:
        return False, f"Offline ❌ ({str(e)[:30]})"

def render_overall_performance(result: Dict[str, Any]):
    """Render the overall performance card matching client UI"""
    overall_score = result.get("overall_score", 0)
    performance_label = result.get("performance_label", "PERFORMANCE")
    grades = result.get("performance_grades", {})
    
    st.markdown(f"""
        <div class="overall-performance">
            <div style="color: #aaa; font-size: 1rem; text-transform: uppercase; letter-spacing: 3px;">
                OVERALL PERFORMANCE
            </div>
            <div class="performance-score">{overall_score}</div>
            <div class="performance-label">{performance_label}</div>
            <div style="margin-top: 30px;">
                <span class="grade-badge">🛡️ DEFENSE: {grades.get('defense_grade', 'B')}</span>
                <span class="grade-badge">⚔️ OFFENSE: {grades.get('offense_grade', 'B')}</span>
                <span class="grade-badge">📍 CONTROL: {grades.get('control_grade', 'B')}</span>
            </div>
        </div>
    """, unsafe_allow_html=True)

def render_skill_breakdown(skills: Dict[str, int]):
    """Render detailed skill breakdown with progress bars"""
    st.markdown("### 📊 SKILL BREAKDOWN")
    st.markdown("<br>", unsafe_allow_html=True)
    
    skill_labels = {
        "offense": ("⚔️", "OFFENSE"),
        "defense": ("🛡️", "DEFENSE"),
        "guard": ("🔒", "GUARD"),
        "passing": ("🚶", "PASSING"),
        "standup": ("🧍", "STANDUP")
    }
    
    for key, (icon, label) in skill_labels.items():
        if key in skills:
            value = skills[key]
            
            # Determine color based on score
            if value >= 85:
                color = "linear-gradient(90deg, #11998e 0%, #38ef7d 100%)"
            elif value >= 70:
                color = "linear-gradient(90deg, #667eea 0%, #764ba2 100%)"
            else:
                color = "linear-gradient(90deg, #ee0979 0%, #ff6a00 100%)"
            
            st.markdown(f"""
                <div class="skill-card">
                    <div class="skill-label">{icon} {label}</div>
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <div class="skill-score">{value}%</div>
                    </div>
                    <div class="progress-bar-custom">
                        <div class="progress-fill" style="width: {value}%; background: {color};"></div>
                    </div>
                </div>
            """, unsafe_allow_html=True)

def render_strengths_weaknesses(strengths: list, weaknesses: list):
    """Render strengths and weaknesses side by side"""
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### ✅ STRENGTHS")
        for i, strength in enumerate(strengths, 1):
            st.markdown(f"""
                <div class="strength-card">
                    <div style="color: #38ef7d; font-weight: 700; margin-bottom: 8px;">
                        ✓ Strength {i}
                    </div>
                    <div style="color: #ddd;">
                        {strength}
                    </div>
                </div>
            """, unsafe_allow_html=True)
    
    with col2:
        st.markdown("### ⚠️ WEAKNESSES")
        for i, weakness in enumerate(weaknesses, 1):
            st.markdown(f"""
                <div class="weakness-card">
                    <div style="color: #ff6a00; font-weight: 700; margin-bottom: 8px;">
                        ✗ Weakness {i}
                    </div>
                    <div style="color: #ddd;">
                        {weakness}
                    </div>
                </div>
            """, unsafe_allow_html=True)

def render_opportunities(opportunities: list):
    if not opportunities:
        return

    st.markdown("### 💡 OPPORTUNITIES MISSED")
    st.markdown("<br>", unsafe_allow_html=True)

    for i, opp in enumerate(opportunities, 1):
        timestamp = opp.get("time", "00:00")
        title = opp.get("title", "Opportunity")
        description = opp.get("description", "")
        category = opp.get("category", "GENERAL")

        st.markdown(f"""
            <div class="opportunity-card">
                <div style="display: flex; align-items: center; margin-bottom: 12px;">
                    <div style="background: #e94560; color: white; width: 35px; height: 35px;
                                border-radius: 50%; display: flex; align-items: center;
                                justify-content: center; font-weight: 800; margin-right: 15px;">
                        {i}
                    </div>
                    <span class="timestamp-badge">{timestamp}</span>
                    <span class="category-badge">{category}</span>
                </div>
                <div style="color: #e94560; font-weight: 700; font-size: 1.1rem; margin-bottom: 8px;">
                    {title}
                </div>
                <div style="color: #ccc;">
                    {description}
                </div>
            </div>
        """, unsafe_allow_html=True)
         # ✅ DEBUG LINE GOES HERE
        st.write("Has frame:", bool(opp.get("frame_image")))

        # ✅ MOVE IMAGE INSIDE LOOP
        if opp.get("frame_image"):
            st.image(
                base64.b64decode(opp["frame_image"]),
                caption=f"Frame @ {timestamp}",
                use_container_width=True
            )




def render_key_moments(moments: list):
    if not moments:
        return

    st.markdown("### ⭐ KEY MOMENTS")
    st.markdown("<br>", unsafe_allow_html=True)

    for i, moment in enumerate(moments, 1):
        timestamp = moment.get("time", "00:00")
        title = moment.get("title", "Event")
        description = moment.get("description", "")
        category = moment.get("category", "GENERAL")

        with st.expander(f"⏱️ {timestamp} - {title}", expanded=False):
            st.markdown(f"""
                <div style="padding: 10px;">
                    <span class="category-badge">{category}</span>
                    <div style="color: #ddd; margin-top: 15px; line-height: 1.6;">
                        {description}
                    </div>
                </div>
            """, unsafe_allow_html=True)
             # ✅ DEBUG LINE GOES HERE
            st.write("Has frame:", bool(moment.get("frame_image")))

            # ✅ IMAGE MUST BE INSIDE EXPANDER + LOOP
            if moment.get("frame_image"):
                st.image(
                    base64.b64decode(moment["frame_image"]),
                    caption=f"Frame @ {timestamp}",
                    use_container_width=True
                )





def render_coach_notes(notes: str):
    """Render coach's insights section"""
    st.markdown("""
        <div class="coach-notes-section">
            <div style="display: flex; align-items: center; margin-bottom: 20px;">
                <div style="font-size: 2rem; margin-right: 15px;">🧑‍🏫</div>
                <div style="font-size: 1.5rem; font-weight: 700; color: #667eea;">
                    COACH'S INSIGHTS
                </div>
            </div>
            <div style="color: #ddd; line-height: 1.8; font-size: 1.05rem;">
    """, unsafe_allow_html=True)
    
    st.markdown(notes)
    
    st.markdown("</div></div>", unsafe_allow_html=True)

def render_recommended_drills(drills: list):
    """Render training drills with detailed information"""
    st.markdown("### 🎓 RECOMMENDED DRILLS")
    st.markdown("<br>", unsafe_allow_html=True)
    
    for i, drill in enumerate(drills, 1):
        name = drill.get("name", "Training Drill")
        focus = drill.get("focus_area", "General")
        reason = drill.get("reason", "")
        duration = drill.get("duration", "15 min/day")
        frequency = drill.get("frequency", "5x/week")
        
        st.markdown(f"""
            <div class="drill-card">
                <div class="drill-header">
                    {i}. {name}
                </div>
                <div style="margin: 15px 0;">
                    <span class="drill-meta">⏱️ {duration}</span>
                    <span class="drill-meta">📅 {frequency}</span>
                </div>
                <div style="color: #aaa; font-size: 0.9rem; margin-bottom: 8px;">
                    <strong>Focus Area:</strong> {focus}
                </div>
                <div style="color: #ddd; line-height: 1.6;">
                    <strong>Why:</strong> {reason}
                </div>
            </div>
        """, unsafe_allow_html=True)

def display_analysis_results(results: Dict[str, Any]):
    """Main function to display all analysis results"""
    if not results:
        st.warning("No results to display")
        return
    
    # Check if fallback was used
    used_fallback = results.get("used_fallback", False)
    if used_fallback:
        st.markdown("""
            <div class="fallback-warning">
                <div style="font-weight: 700; font-size: 1.1rem; margin-bottom: 10px;">
                    ⚠️ Analysis Used Fallback Mode
                </div>
                <div style="color: #ddd;">
                    The AI encountered processing difficulties. Results are based on general BJJ principles 
                    and may be less specific than usual. For best results, ensure good lighting and clear footage.
                </div>
            </div>
        """, unsafe_allow_html=True)
    
    # Extract data
    data = results.get("data", {})
    if not data:
        data = results
    
    # Processing time (Display from result or added by client)
    if "processing_time" in results:
        st.caption(f"⚡ Analysis completed in {results['processing_time']}")
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    # Overall Performance
    render_overall_performance(data)
    
    st.markdown("<br><br>", unsafe_allow_html=True)
    
    # Skill Breakdown
    if "skill_breakdown" in data:
        render_skill_breakdown(data["skill_breakdown"])
    
    st.markdown("<br><br>", unsafe_allow_html=True)
    
    # Strengths & Weaknesses
    if "strengths" in data and "weaknesses" in data:
        render_strengths_weaknesses(data["strengths"], data["weaknesses"])
    
    st.markdown("<br><br>", unsafe_allow_html=True)
    
    # Missed Opportunities
    if "missed_opportunities" in data:
        render_opportunities(data["missed_opportunities"])
    
    st.markdown("<br><br>", unsafe_allow_html=True)
    
    # Key Moments
    if "key_moments" in data:
        render_key_moments(data["key_moments"])
    
    st.markdown("<br><br>", unsafe_allow_html=True)
    
    # Coach's Notes
    if "coach_notes" in data:
        render_coach_notes(data["coach_notes"])
    
    st.markdown("<br><br>", unsafe_allow_html=True)
    
    # Recommended Drills
    if "recommended_drills" in data:
        render_recommended_drills(data["recommended_drills"])

def main():

    # ---- Session guards (CRITICAL) ----
    if "analysis_running" not in st.session_state:
        st.session_state.analysis_running = False

    if "analysis_result" not in st.session_state:
        st.session_state.analysis_result = None

    st.markdown('<h1 class="main-title">🥋 BJJ AI COACH</h1>', unsafe_allow_html=True)
    st.markdown('<p class="subtitle">Advanced Performance Analysis Powered by AI</p>', unsafe_allow_html=True)
    
    # Backend Status
    online, status_msg = check_backend_health(BJJ_BACKEND_URL)
    
    if not online:
        st.error(f"⚠️ Backend Connection Failed: {status_msg}")
        st.code("uvicorn main:app --host 0.0.0.0 --port 8000 --reload", language="bash")
        if st.button("🔄 Retry Connection"):
            st.rerun()
        return
    else:
        st.success(f"✅ System Status: {status_msg}")
    
    st.markdown("---")
    
    # Main Input Section
    col1, col2 = st.columns([1.2, 1])
    
    with col1:
        st.markdown("### 📹 UPLOAD VIDEO")
        uploaded_file = st.file_uploader(
            "Select sparring footage",
            type=["mp4", "avi", "mov", "mkv", "webm"],
            help="Supported formats: MP4, AVI, MOV, MKV, WebM"
        )
        
        if uploaded_file:
            st.success(f"✓ Loaded: {uploaded_file.name} ({uploaded_file.size / 1024 / 1024:.2f} MB)")
    
    with col2:
        st.markdown("### ⚙️ MATCH CONFIGURATION")
        user_desc = st.text_input(
            "👤 Your Description",
            value="Player with dark brown hair",
            help="Describe yourself (gi color, appearance, etc.)"
        )
        opp_desc = st.text_input(
            "🥊 Opponent Description",
            value="Player with blonde hair",
            help="Describe your opponent"
        )
        activity = st.selectbox(
            "🥋 Activity Type",
            ["Brazilian Jiu-Jitsu", "No-Gi Grappling", "Judo", "Wrestling", "MMA Grappling"]
        )
    
    st.markdown("---")
    
    # Analysis Button
    if uploaded_file and online:
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            analyze_button = st.button(
                "🚀 START ANALYSIS",
                type="primary",
                use_container_width=True
            )
        
        if analyze_button and not st.session_state.analysis_running:
            st.session_state.analysis_running = True
            st.session_state.analysis_result = None
            progress_container = st.container()
            
            with progress_container:
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                try:
                    # Upload phase
                    status_text.markdown("**📤 Uploading video to server...**")
                    progress_bar.progress(10)
                    time.sleep(0.3)
                    
                    status_text.markdown("**🎬 Extracting key frames...**")
                    progress_bar.progress(25)
                    
                    # Prepare request
                    files = {
                        "file": (uploaded_file.name, uploaded_file.getvalue(), uploaded_file.type)
                    }
                    data = {
                        "user_description": user_desc,
                        "opponent_description": opp_desc,
                        "activity_type": activity
                    }
                    
                    status_text.markdown("**🤖 AI analyzing technique...**")
                    progress_bar.progress(40)
                    
                    # Start timer
                    start_time = time.time()
                    
                    # Make API call
                    response = requests.post(
                        f"{BJJ_BACKEND_URL}/analyze-complete",
                        files=files,
                        data=data,
                        timeout=180  # 3 minutes max
                    )
                    
                    # End timer
                    end_time = time.time()
                    processing_duration = f"{end_time - start_time:.2f}s"
                    
                    progress_bar.progress(90)
                    
                    if response.status_code == 200:
                        result = response.json()
                        
                        if result.get("status") in ["completed", "completed_with_fallback"]:
                            progress_bar.progress(100)
                            status_text.success("✅ Analysis Complete!")
                            time.sleep(1)
                            
                            # Clear progress
                            progress_bar.empty()
                            status_text.empty()
                            
                            # Add client-side timing if not present
                            if "processing_time" not in result:
                                result["processing_time"] = processing_duration
                            else:
                                # Show both if available, or stick to backend time. 
                                # Here we append client time to the existing string for clarity
                                result["processing_time"] = f"{result['processing_time']} (Total: {processing_duration})"
                            
                            st.markdown("---")
                            
                            # Display Results
                            st.session_state.analysis_result = result

                            
                            # Download Button
                            st.markdown("<br><br>", unsafe_allow_html=True)
                            col1, col2, col3 = st.columns([1, 2, 1])
                            with col2:
                                json_str = json.dumps(result.get("data", {}), indent=2)
                                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                                st.download_button(
                                    "📥 Download Full Analysis (JSON)",
                                    json_str,
                                    file_name=f"bjj_analysis_{timestamp}.json",
                                    mime="application/json",
                                    use_container_width=True
                                )
                        else:
                            st.error(f"❌ Analysis failed: {result.get('error', 'Unknown error')}")
                    
                    else:
                        st.error(f"❌ Server returned error {response.status_code}")
                        st.code(response.text[:500])
                
                except requests.exceptions.Timeout:
                    st.error("⏱️ Request timed out. Video may be too long. Try a shorter clip.")
                except requests.exceptions.ConnectionError:
                    st.error("🔌 Connection error. Ensure the backend is running.")
                except Exception as e:
                    st.error(f"❌ Error: {str(e)}")
                finally:
                    st.session_state.analysis_running = False
                    progress_bar.empty()
                    status_text.empty()
    # ===============================
    # DISPLAY RESULT (SAFE LOCATION)
    # ===============================
    if st.session_state.analysis_result:
        st.markdown("---")
        display_analysis_results(st.session_state.analysis_result)

    
    # Sidebar
    with st.sidebar:
        st.markdown("### ⚙️ SYSTEM INFO")
        st.info(f"Backend: `{BJJ_BACKEND_URL}`")
        
        st.markdown("---")
        st.markdown("### 📖 HOW IT WORKS")
        st.markdown("""
        1. **Upload** your sparring video
        2. **Describe** who's who clearly
        3. **Wait** 15-45s for AI processing
        4. **Review** detailed tactical analysis
        5. **Download** JSON for record-keeping
        """)
        
        st.markdown("---")
        st.markdown("### 💡 TIPS FOR BEST RESULTS")
        st.markdown("""
        - Use **good lighting**
        - **Side angle** camera view preferred
        - Keep both athletes **in frame**
        - **15-60 second** clips work best
        - Clearly distinguish athletes (gi color/appearance)
        """)
        
        st.markdown("---")
        st.markdown("### 🔧 TECHNICAL SPECS")
        st.markdown("""
        - **Model**: Gemini 2.5 Flash
        - **Frame Analysis**: 8-24 frames
        - **Retry System**: 3 attempts with fallback
        - **Accuracy**: Position detection, submissions
        """)
        
        st.markdown("---")
        st.caption("Built with ❤️ for the BJJ community")

if __name__ == "__main__":
    main()