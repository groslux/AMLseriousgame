 (cd "$(git rev-parse --show-toplevel)" && git apply --3way <<'EOF' 
diff --git a/aml_mastermind_final.py b/aml_mastermind_final.py
index 679cc3e084e7e43b73bf8ade80a672368fccdf6e..b48fb1463d722ba370b60d44189d94564b58d838 100644
--- a/aml_mastermind_final.py
+++ b/aml_mastermind_final.py
@@ -86,68 +86,59 @@ if st.session_state.step == "mode":
         st.session_state.done = False
         st.session_state.start_time = time.time()
         st.session_state.step = "quiz"
    
     st.stop()
 
 # --- Step: Quiz ---
 if st.session_state.step == "quiz":
     questions = st.session_state.questions
     idx = st.session_state.current
     mode = st.session_state.mode
 
     if mode == "Time Attack":
         elapsed = int(time.time() - st.session_state.start_time)
         time_left = st.session_state.max_time - elapsed
         if time_left <= 0 or idx >= len(questions):
             st.session_state.done = True
             st.session_state.step = "result"
   
         st.markdown(f"⏳ Time left: **{time_left} seconds**")
 
     if idx < len(questions):
         q = questions[idx]
         st.markdown(f"### Q{idx + 1}: {q['question']}")
         st.progress((idx + 1) / len(questions))
-        with st.form(key=f"form_{idx}"):        
-            shuffle_key = f"shuffled_{idx}"
+        shuffle_key = f"shuffled_{idx}"
         if shuffle_key not in st.session_state:
             opts = q["options"].copy()
             random.shuffle(opts)
             st.session_state[shuffle_key] = opts
         else:
             opts = st.session_state[shuffle_key]
 
-            sel = st.radio("Choose an answer:", opts, key=f"answer_{idx}")
-
-
-
-
-            sel = st.radio("Choose an answer:", opts, key=f"answer_{idx}")
-
-            opts = q["options"].copy()
-            random.shuffle(opts)
+        with st.form(key=f"form_{idx}"):
             sel = st.radio("Choose an answer:", opts, key=f"answer_{idx}")
             submitted = st.form_submit_button("Submit")
 
         if submitted:
             correct = q["correct_answer"]
             is_correct = (sel.strip().casefold() == correct.strip().casefold())
             st.session_state.answers.append(is_correct)
 
             if is_correct:
                 st.success("✅ Correct!")
             else:
                 st.error(f"❌ Wrong! Correct answer: **{correct}**")
             st.caption(f"**Explanation:** {q['explanation']}  \n🔗 **Source:** {q['source']}")
 
             st.session_state.current += 1
             time.sleep(0.3)
             if mode == "Classic Quiz" and st.session_state.current >= len(questions):
                 st.session_state.done = True
                 st.session_state.step = "result"
       
     else:
         st.session_state.done = True
         st.session_state.step = "result"
  
 
 
EOF
)
