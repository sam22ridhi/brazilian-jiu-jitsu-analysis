from __future__ import annotations
import os
import time
import shutil
import uuid
import json
import asyncio
import base64
import re
from typing import List, Optional, Dict, Any
from fastapi import FastAPI, UploadFile, File, BackgroundTasks, HTTPException, Form
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, ConfigDict
import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold
import cv2
import numpy as np

# Configuration
GEMINI_API_KEY = os.getenv("GOOGLE_API_KEY")
genai.configure(api_key=GEMINI_API_KEY)

app = FastAPI(title="BJJ AI Coach - Smart Frame Extraction")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- MODELS ---

class TimestampedEvent(BaseModel):
    time: str
    title: str
    description: str
    category: Optional[str] = "GENERAL"
    frame_image: Optional[str] = None
    frame_timestamp: Optional[str] = None
    
    model_config = ConfigDict(extra="allow")

class Drill(BaseModel):
    name: str
    focus_area: str
    reason: str
    duration: Optional[str] = "15 min/day"
    frequency: Optional[str] = "5x/week"

class DetailedSkillBreakdown(BaseModel):
    offense: int
    defense: int
    guard: int
    passing: int
    standup: int

class PerformanceGrades(BaseModel):
    defense_grade: str
    offense_grade: str
    control_grade: str

class AnalysisResult(BaseModel):
    overall_score: int
    performance_label: str
    performance_grades: PerformanceGrades
    skill_breakdown: DetailedSkillBreakdown
    strengths: List[str]
    weaknesses: List[str]
    missed_opportunities: List[TimestampedEvent]
    key_moments: List[TimestampedEvent]
    coach_notes: str
    recommended_drills: List[Drill]

db_storage = {}

# --- UTILITY FUNCTIONS ---

def parse_time_to_seconds(time_str: str) -> Optional[int]:
    if not time_str:
        return None
    match = re.search(r"(\d{1,2}):(\d{2})", time_str)
    if not match:
        return None
    mm, ss = match.groups()
    return int(mm) * 60 + int(ss)

def find_closest_frame(target_time_sec: int, frames: list) -> dict:
    return min(frames, key=lambda f: abs(f["second"] - target_time_sec))

def attach_frames_to_events(events: List[dict], frames: list):
    for event in events:
        try:
            event_time_sec = parse_time_to_seconds(event.get("time"))
            if event_time_sec is None:
                continue
            closest = find_closest_frame(event_time_sec, frames)
            event["frame_timestamp"] = closest["timestamp"]
            event["frame_image"] = base64.b64encode(closest["bytes"]).decode("utf-8")
        except Exception as e:
            print(f"⚠️ Frame attachment failed: {e}")
            event["frame_image"] = None

def extract_json_from_text(text: str) -> Dict:
    text = text.strip()
    
    try:
        return json.loads(text)
    except:
        pass
    
    if "```json" in text or "```" in text:
        try:
            if "```json" in text:
                text = text.split("```json")[1].split("```")[0]
            else:
                text = text.split("```")[1].split("```")[0]
            return json.loads(text.strip())
        except:
            pass
    
    try:
        start_idx = text.find('{')
        if start_idx == -1:
            raise ValueError("No opening brace")
        
        brace_count = 0
        end_idx = -1
        
        for i in range(start_idx, len(text)):
            if text[i] == '{':
                brace_count += 1
            elif text[i] == '}':
                brace_count -= 1
                if brace_count == 0:
                    end_idx = i
                    break
        
        if end_idx == -1:
            raise ValueError("No closing brace")
        
        json_str = text[start_idx:end_idx+1]
        return json.loads(json_str)
    except:
        pass
    
    raise ValueError(f"Could not extract JSON from: {text[:300]}")

# --- SMART WEIGHTED FRAME EXTRACTION ---

def extract_smart_weighted_frames(video_path: str) -> tuple:
    """
    Extract frames with WEIGHTED PRIORITY:
    - START (first 20%): 4-5 frames (shows initial position/setup)
    - MIDDLE (20-80%): 4-5 frames (shows flow/transitions)
    - END (last 20%): 6-7 frames (CRITICAL - shows finish/submission)
    
    Total: 14-16 frames optimized for outcome detection
    """
    try:
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            raise Exception("Cannot open video")
        
        fps = cap.get(cv2.CAP_PROP_FPS)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        duration = total_frames / fps if fps > 0 else 0
        
        # Determine total frames to extract based on duration
        if duration <= 30:
            total_to_extract = 14
        elif duration <= 60:
            total_to_extract = 16
        else:
            total_to_extract = 18
        
        print(f"📹 Smart extraction from {duration:.1f}s video")
        print(f"   Total frames: {total_to_extract}")
        
        # WEIGHTED ALLOCATION
        # Prioritize END (where submissions happen)
        start_frames = max(4, int(total_to_extract * 0.25))  # 25% for start
        end_frames = max(6, int(total_to_extract * 0.40))     # 40% for end (MOST IMPORTANT)
        middle_frames = total_to_extract - start_frames - end_frames  # Remaining for middle
        
        print(f"   Start: {start_frames} | Middle: {middle_frames} | End: {end_frames}")
        
        # Define sections
        start_section_end = int(total_frames * 0.20)  # First 20%
        end_section_start = int(total_frames * 0.80)  # Last 20%
        
        frames = []
        
        # SECTION 1: START (First 20% - Initial position)
        print("   📍 Extracting START frames...")
        start_interval = max(1, start_section_end // start_frames)
        for i in range(0, start_section_end, start_interval):
            if len([f for f in frames if f["second"] < duration * 0.20]) >= start_frames:
                break
            frame = extract_frame_at_index(cap, i, fps)
            if frame:
                frames.append(frame)
        
        # SECTION 2: MIDDLE (20-80% - Flow/transitions)
        print("   📍 Extracting MIDDLE frames...")
        middle_section_frames = end_section_start - start_section_end
        middle_interval = max(1, middle_section_frames // middle_frames)
        for i in range(start_section_end, end_section_start, middle_interval):
            if len([f for f in frames if duration * 0.20 <= f["second"] < duration * 0.80]) >= middle_frames:
                break
            frame = extract_frame_at_index(cap, i, fps)
            if frame:
                frames.append(frame)
        
        # SECTION 3: END (Last 20% - CRITICAL for submissions)
        print("   📍 Extracting END frames (CRITICAL)...")
        end_section_frames = total_frames - end_section_start
        end_interval = max(1, end_section_frames // end_frames)
        for i in range(end_section_start, total_frames, end_interval):
            if len([f for f in frames if f["second"] >= duration * 0.80]) >= end_frames:
                break
            frame = extract_frame_at_index(cap, i, fps)
            if frame:
                frames.append(frame)
        
        # BONUS: Always include the VERY LAST frame (most likely to show submission)
        last_frame = extract_frame_at_index(cap, total_frames - 1, fps)
        if last_frame and last_frame not in frames:
            print("   ⭐ Adding FINAL frame (critical for tap detection)")
            frames.append(last_frame)
        
        cap.release()
        
        # Sort by timestamp
        frames.sort(key=lambda f: f["second"])
        
        metadata = {
            "duration": round(duration, 2),
            "fps": round(fps, 2),
            "frames_extracted": len(frames),
            "distribution": {
                "start": start_frames,
                "middle": middle_frames,
                "end": end_frames
            }
        }
        
        print(f"✓ Extracted {len(frames)} frames with weighted distribution")
        print(f"   Distribution: START={len([f for f in frames if f['second'] < duration * 0.20])}, "
              f"MIDDLE={len([f for f in frames if duration * 0.20 <= f['second'] < duration * 0.80])}, "
              f"END={len([f for f in frames if f['second'] >= duration * 0.80])}")
        
        return frames, metadata
        
    except Exception as e:
        if 'cap' in locals():
            cap.release()
        raise Exception(f"Frame extraction failed: {str(e)}")

def extract_frame_at_index(cap: cv2.VideoCapture, frame_idx: int, fps: float) -> Optional[dict]:
    """Extract a single frame at given index"""
    try:
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
        ret, frame = cap.read()
        
        if not ret:
            return None
        
        # Resize to 720p
        h, w = frame.shape[:2]
        target_h = 720
        target_w = int(w * (target_h / h))
        resized = cv2.resize(frame, (target_w, target_h))
        
        # Encode to JPEG
        _, buffer = cv2.imencode('.jpg', resized, [cv2.IMWRITE_JPEG_QUALITY, 85])
        
        # Calculate timestamp
        timestamp_sec = frame_idx / fps
        timestamp_str = f"{int(timestamp_sec // 60):02d}:{int(timestamp_sec % 60):02d}"
        
        return {
            "bytes": buffer.tobytes(),
            "timestamp": timestamp_str,
            "second": round(timestamp_sec, 2),
            "frame_idx": frame_idx
        }
    except Exception as e:
        print(f"⚠️ Failed to extract frame {frame_idx}: {e}")
        return None

# --- SUBMISSION-AWARE PROMPT ---

SUBMISSION_AWARE_PROMPT = """You are an expert BJJ black belt coach analyzing training footage.

**ATHLETES:**
- User (YOU ARE ANALYZING THIS PERSON): {user_desc}
- Opponent: {opp_desc}

**VIDEO INFO:**
- Duration: {duration}s
- Frames: {num_frames} snapshots (weighted toward START and END)

**FRAME DISTRIBUTION:**
- START frames ({start_frames}): Initial setup, opening position
- MIDDLE frames ({middle_frames}): Flow, transitions, scrambles
- END frames ({end_frames}): CRITICAL - Final position, potential submission/tap

**FRAME TIMELINE:**
{frame_list}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚠️ CRITICAL: SUBMISSION & TAP DETECTION ⚠️
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

**YOUR #1 JOB: Check the LAST 6-7 frames for a submission finish**

The END frames (last 20% of video) are MOST IMPORTANT because:
- This is where matches typically end
- This is where submissions happen
- This is where taps occur

**Visual Tap Indicators:**
- ✅ Hand rapidly slapping mat (2+ times)
- ✅ Hand rapidly slapping opponent's body (2+ times)
- ✅ Verbal tap (mouth open, grimacing, yelling)
- ✅ Body going limp / giving up resistance
- ✅ Someone releasing a hold after achieving it

**Frame-by-Frame Analysis for END:**

Look at the LAST frames sequentially:
1. Frame N-6: What position? Any submission setups?
2. Frame N-5: Position changing? Submission being applied?
3. Frame N-4: Is control tightening? Any distress visible?
4. Frame N-3: Is opponent grimacing? Defensive hands visible?
5. Frame N-2: Any tapping motion? Is hold fully locked?
6. Frame N-1: Match still going or released/ended?
7. Frame N (LAST): Final position - why did it end here?

**If you see this pattern in final frames:**
- Early frames: User controlling leg/neck/arm
- Middle frames: Pressure increasing, opponent reacting
- Final frames: Opponent tapping OR match ending with hold locked
- **CONCLUSION: User finished with submission**

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

## LEG LOCK SPECIFIC DETECTION (Common in No-Gi)

**Straight Ankle Lock / Achilles Lock:**
- User has opponent's foot trapped (heel against chest/armpit)
- User's hands gripping around ankle/Achilles
- User arching back / falling back (finish motion)
- Opponent's leg extended and under tension
- **If you see this + opponent tapping = ANKLE LOCK FINISH**

**Heel Hook:**
- User controlling opponent's leg with inside or outside position
- User's arm wrapping opponent's heel
- Rotational pressure visible
- **If you see this + tap = HEEL HOOK FINISH**

**Knee Bar:**
- User controlling opponent's leg across their hip
- Opponent's knee hyperextended
- **If you see this + tap = KNEE BAR FINISH**

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

## CHOKE DETECTION

**Rear-Naked Choke:**
- User behind opponent (back control)
- User's arm(s) around opponent's neck
- **If you see this + tap = RNC FINISH**

**Triangle / Guillotine:**
- Leg around neck OR arm around neck
- **If you see this + tap = CHOKE FINISH**

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

## SCORING RULES (OUTCOME-BASED)

**IF USER WON BY SUBMISSION:**
- Offense: 80-95 (Finished = elite offense)
- Defense: 75-85 (Never in danger)
- Overall: 80-92 (Submission victory = strong/excellent)
- Label: "STRONG PERFORMANCE" or "EXCELLENT PERFORMANCE"

**IF OPPONENT WON BY SUBMISSION:**
- Offense: 40-60 (Couldn't finish)
- Defense: 25-40 (Got submitted = critical failure)
- Overall: 40-60 (Submitted = needs work)
- Label: "DEVELOPING" or "NEEDS IMPROVEMENT"

**IF NO SUBMISSION (positional only):**
- Score based on control and dominance
- Most recreational = 55-70

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

## MANDATORY OUTPUT REQUIREMENTS

**If submission occurred:**

1. **Strengths #1 MUST be:**
   "At [TIME] - Successfully finished [OPPONENT/USER] with [TECHNIQUE], demonstrating excellent [specific skill]"

2. **Key Moments MUST include:**
   {{"time": "[TIME]", "title": "Match-Ending Submission", "description": "[Winner] submitted [Loser] via [TECHNIQUE]", "category": "SUBMISSION"}}

3. **Coach's Notes MUST start with:**
   "The match ended at [TIME] with [Winner] submitting [Loser] via [TECHNIQUE]..."

4. **Recommended Drill #1:**
   - If User won: "Drill to refine [TECHNIQUE] finish"
   - If User lost: "Drill to defend [TECHNIQUE] that caught you"

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

## OUTPUT FORMAT (JSON ONLY)

{{
  "overall_score": <int 0-100>,
  "performance_label": "EXCELLENT|STRONG|SOLID|DEVELOPING|NEEDS IMPROVEMENT",
  "performance_grades": {{
    "defense_grade": "<letter>",
    "offense_grade": "<letter>",
    "control_grade": "<letter>"
  }},
  "skill_breakdown": {{
    "offense": <int 0-100>,
    "defense": <int 0-100>,
    "guard": <int 0-100>,
    "passing": <int 0-100>,
    "standup": <int 0-100>
  }},
  "strengths": [
    "At 0:XX - [SUBMISSION FINISH if occurred, otherwise best moment]",
    "At 0:XX - Second strength",
    "At 0:XX - Third strength"
  ],
  "weaknesses": [
    "At 0:XX - [GOT SUBMITTED if occurred, otherwise main weakness]",
    "At 0:XX - Second weakness",
    "At 0:XX - Third weakness"
  ],
  "missed_opportunities": [
    {{"time": "00:XX", "title": "...", "description": "...", "category": "SUBMISSION|SWEEP|POSITION"}}
  ],
  "key_moments": [
    {{"time": "00:XX", "title": "Match-Ending Submission", "description": "[Winner] submitted [Loser] via [TECHNIQUE]", "category": "SUBMISSION"}},
    {{"time": "00:XX", "title": "...", "description": "...", "category": "TRANSITION|DEFENSE|SWEEP"}}
  ],
  "coach_notes": "The match ended at [TIME] with [outcome]. [Detailed analysis of path to finish]...",
  "recommended_drills": [
    {{"name": "...", "focus_area": "...", "reason": "[Address submission outcome]", "duration": "15 min/day", "frequency": "5x/week"}},
    {{"name": "...", "focus_area": "...", "reason": "...", "duration": "10 min/day", "frequency": "4x/week"}},
    {{"name": "...", "focus_area": "...", "reason": "...", "duration": "12 min/day", "frequency": "3x/week"}}
  ]
}}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

## FINAL CHECKLIST

- [ ] Did I analyze the LAST 6-7 frames carefully?
- [ ] Did I look for leg control → tension → tapping pattern?
- [ ] If I saw a submission hold in final frames, did I check for tap?
- [ ] Did I identify WHO tapped (User or Opponent)?
- [ ] Did I score appropriately for submission outcome?
- [ ] Did I list submission as #1 in strengths/weaknesses?
- [ ] Did I include submission in key moments?
- [ ] Did I start coach's notes with submission outcome?

**REMEMBER:** The END frames are WEIGHTED MORE HEAVILY for this exact reason!
"""

# --- ANALYSIS PIPELINE ---

async def fast_accurate_analysis(
    frames: List[Dict],
    metadata: Dict,
    user_desc: str,
    opp_desc: str,
    activity_type: str,
    analysis_id: str = None
) -> AnalysisResult:
    """Submission-aware analysis with smart weighted frames"""
    
    print("\n" + "="*70)
    print("🎯 SUBMISSION-AWARE ANALYSIS (Smart Weighted Frames)")
    print("="*70)
    
    try:
        # AGENT 1: GEMINI VISION
        print("\n🤖 AGENT 1: Gemini Vision Analysis")
        if analysis_id:
            db_storage[analysis_id]["progress"] = 50
        
        # Build frame list with section labels
        frame_list_parts = []
        duration = metadata["duration"]
        
        for i, f in enumerate(frames):
            section = "START" if f["second"] < duration * 0.20 else ("END" if f["second"] >= duration * 0.80 else "MIDDLE")
            frame_list_parts.append(f"Frame {i+1} @ {f['timestamp']} ({f['second']}s) [{section}]")
        
        frame_list = "\n".join(frame_list_parts)
        
        # Get distribution
        dist = metadata.get("distribution", {})
        
        prompt = SUBMISSION_AWARE_PROMPT.format(
            user_desc=user_desc,
            opp_desc=opp_desc,
            duration=duration,
            num_frames=len(frames),
            start_frames=dist.get("start", 4),
            middle_frames=dist.get("middle", 4),
            end_frames=dist.get("end", 6),
            frame_list=frame_list
        )
        
        # Prepare content
        content = [
            {
                "mime_type": "image/jpeg",
                "data": base64.b64encode(f["bytes"]).decode("utf-8")
            }
            for f in frames
        ]
        content.append(prompt)
        
        # Call Gemini
        start = time.time()
        model = genai.GenerativeModel(
            model_name="gemini-2.5-flash",
            generation_config={
                "temperature": 0.2,
                "response_mime_type": "application/json",
                "max_output_tokens": 4000
            }
        )
        
        response = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: model.generate_content(
                content,
                safety_settings={
                    HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
                    HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
                    HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
                    HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
                }
            )
        )
        
        gemini_time = time.time() - start
        print(f"✓ Gemini analysis: {gemini_time:.2f}s")
        
        # AGENT 2: PARSE & ENHANCE
        print("\n📊 AGENT 2: Parse & Enhance")
        if analysis_id:
            db_storage[analysis_id]["progress"] = 90
        
        result_data = extract_json_from_text(response.text)
        result_data = validate_analysis(result_data)
        
        print("🖼️ Attaching frames to events...")
        attach_frames_to_events(result_data.get("missed_opportunities", []), frames)
        attach_frames_to_events(result_data.get("key_moments", []), frames)
        
        if analysis_id:
            db_storage[analysis_id]["progress"] = 100
        
        total_time = time.time() - start
        print(f"\n✅ COMPLETE in {total_time:.2f}s")
        print("="*70 + "\n")
        
        return AnalysisResult(**result_data)
    
    except Exception as e:
        print(f"\n❌ Analysis failed: {str(e)}")
        fallback = generate_fallback()
        if analysis_id:
            db_storage[analysis_id]["used_fallback"] = True
        return AnalysisResult(**fallback)

def validate_analysis(data: Dict) -> Dict:
    if "overall_score" not in data:
        data["overall_score"] = 65
    data["overall_score"] = max(0, min(100, data["overall_score"]))
    
    if "performance_label" not in data:
        score = data["overall_score"]
        if score >= 85:
            data["performance_label"] = "EXCELLENT PERFORMANCE"
        elif score >= 75:
            data["performance_label"] = "STRONG PERFORMANCE"
        elif score >= 60:
            data["performance_label"] = "SOLID PERFORMANCE"
        else:
            data["performance_label"] = "DEVELOPING PERFORMANCE"
    
    if "performance_grades" not in data:
        data["performance_grades"] = {
            "defense_grade": "C+",
            "offense_grade": "C",
            "control_grade": "C+"
        }
    
    if "skill_breakdown" not in data:
        base = data["overall_score"]
        data["skill_breakdown"] = {
            "offense": max(0, min(100, base - 5)),
            "defense": max(0, min(100, base + 3)),
            "guard": max(0, min(100, base - 2)),
            "passing": max(0, min(100, base - 10)),
            "standup": max(0, min(100, base - 13))
        }
    
    for field in ["strengths", "weaknesses"]:
        if field not in data or len(data[field]) < 3:
            default = ["Good structure", "Showed awareness", "Consistent"] if field == "strengths" else ["More aggression", "Improve timing", "Work transitions"]
            data[field] = default
        data[field] = data[field][:3]
    
    for field in ["missed_opportunities", "key_moments"]:
        if field not in data or not data[field]:
            data[field] = [{
                "time": "00:30",
                "title": "Key Moment",
                "description": "Review footage",
                "category": "POSITION"
            }]
    
    if "coach_notes" not in data or len(data["coach_notes"]) < 50:
        data["coach_notes"] = "Focus on fundamentals and consistent positioning."
    
    if "recommended_drills" not in data or len(data["recommended_drills"]) < 3:
        data["recommended_drills"] = [
            {"name": "Position Control", "focus_area": "General", "reason": "Improve awareness", "duration": "15 min/day", "frequency": "5x/week"},
            {"name": "Guard Work", "focus_area": "Defense", "reason": "Strengthen defense", "duration": "10 min/day", "frequency": "4x/week"},
            {"name": "Transitions", "focus_area": "Movement", "reason": "Improve flow", "duration": "12 min/day", "frequency": "3x/week"}
        ]
    
    return data

def generate_fallback() -> Dict:
    return {
        "overall_score": 65,
        "performance_label": "SOLID PERFORMANCE",
        "performance_grades": {"defense_grade": "C+", "offense_grade": "C", "control_grade": "C+"},
        "skill_breakdown": {"offense": 60, "defense": 68, "guard": 63, "passing": 55, "standup": 52},
        "strengths": ["Maintained defensive structure", "Showed positional awareness", "Consistent movement"],
        "weaknesses": ["Could be more aggressive", "Improve transition recognition", "Work on timing"],
        "missed_opportunities": [{"time": "00:30", "title": "Position", "description": "Review for openings", "category": "POSITION"}],
        "key_moments": [{"time": "00:15", "title": "Exchange", "description": "Positional work", "category": "TRANSITION"}],
        "coach_notes": "Focus on fundamentals: maintain posture, control distance, look for position improvement.",
        "recommended_drills": [
            {"name": "Positional Sparring", "focus_area": "General", "reason": "Develop awareness", "duration": "15 min/day", "frequency": "5x/week"},
            {"name": "Guard Work", "focus_area": "Defense", "reason": "Strengthen defense", "duration": "10 min/day", "frequency": "4x/week"},
            {"name": "Position Control", "focus_area": "Control", "reason": "Improve control", "duration": "12 min/day", "frequency": "3x/week"}
        ]
    }

# --- BACKGROUND TASK ---

async def analyze_video_task(
    analysis_id: str,
    video_path: str,
    user_desc: str,
    opp_desc: str,
    activity_type: str
):
    try:
        db_storage[analysis_id]["status"] = "processing"
        db_storage[analysis_id]["progress"] = 10
        
        frames, metadata = await asyncio.get_event_loop().run_in_executor(
            None, extract_smart_weighted_frames, video_path
        )
        
        result = await fast_accurate_analysis(
            frames, metadata, user_desc, opp_desc, activity_type, analysis_id
        )
        
        db_storage[analysis_id]["status"] = "completed"
        db_storage[analysis_id]["data"] = result.model_dump()
    except Exception as e:
        print(f"❌ Task error: {str(e)}")
        fallback = generate_fallback()
        db_storage[analysis_id]["status"] = "completed"
        db_storage[analysis_id]["data"] = fallback
        db_storage[analysis_id]["used_fallback"] = True
    finally:
        try:
            os.remove(video_path)
        except:
            pass

# --- API ENDPOINTS ---

@app.post("/upload")
async def upload_video(file: UploadFile = File(...)):
    file_name = f"{uuid.uuid4()}_{file.filename}"
    file_path = f"temp_videos/{file_name}"
    os.makedirs("temp_videos", exist_ok=True)
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    return {"file_name": file_path}

@app.post("/analyze")
async def start_analysis(
    video_file_name: str,
    user_description: str,
    opponent_description: str,
    activity_type: str = "Brazilian Jiu-Jitsu",
    background_tasks: BackgroundTasks = None
):
    analysis_id = str(uuid.uuid4())
    db_storage[analysis_id] = {"status": "queued", "progress": 0}
    background_tasks.add_task(
        analyze_video_task, analysis_id, video_file_name,
        user_description.strip(), opponent_description.strip(), activity_type
    )
    return {"analysis_id": analysis_id}

@app.get("/status/{analysis_id}")
async def get_status(analysis_id: str):
    if analysis_id not in db_storage:
        raise HTTPException(status_code=404, detail="Not found")
    return db_storage[analysis_id]

@app.post("/analyze-complete")
async def analyze_complete(
    file: UploadFile = File(...),
    user_description: str = Form(...),
    opponent_description: str = Form(...),
    activity_type: str = Form("Brazilian Jiu-Jitsu")
):
    start_time = time.time()
    file_path = None
    
    try:
        file_name = f"{uuid.uuid4()}_{file.filename}"
        file_path = f"temp_videos/{file_name}"
        os.makedirs("temp_videos", exist_ok=True)
        
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        analysis_id = str(uuid.uuid4())
        db_storage[analysis_id] = {"status": "processing", "progress": 0}
        
        frames, metadata = await asyncio.get_event_loop().run_in_executor(
            None, extract_smart_weighted_frames, file_path
        )
        
        result = await fast_accurate_analysis(
            frames, metadata,
            user_description.strip(), opponent_description.strip(),
            activity_type, analysis_id
        )
        
        total_time = time.time() - start_time
        
        return {
            "status": "completed",
            "data": result.model_dump(),
            "processing_time": f"{total_time:.2f}s",
            "used_fallback": db_storage[analysis_id].get("used_fallback", False),
            "method": "smart_weighted_frames"
        }
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        fallback = generate_fallback()
        return {
            "status": "completed_with_fallback",
            "data": fallback,
            "error": str(e),
            "used_fallback": True
        }
    finally:
        if file_path:
            try:
                os.remove(file_path)
            except:
                pass

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "version": "21.0.0-smart-weighted"
    }

@app.get("/")
async def root():
    return {
        "message": "BJJ AI Coach - Smart Weighted Frame Extraction",
        "version": "21.0.0",
        "frame_extraction": {
            "method": "Weighted Priority",
            "distribution": "START 25% | MIDDLE 35% | END 40%",
            "rationale": "END weighted heavily for submission detection"
        },
        "features": [
            "✅ 40% of frames from final 20% of video",
            "✅ Always includes VERY LAST frame",
            "✅ Frame-by-frame END analysis in prompt",
            "✅ Explicit leg lock detection patterns",
            "✅ Tap detection visual indicators",
            "✅ Outcome-based scoring adjustments"
        ],
        "target_time": "30-45 seconds"

    }
