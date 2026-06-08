# The IMAC Module

import ollama
import json
import re
import sys
import os


def extract_tag(text, tag):
   pattern = rf"<{tag}>\s*(.*?)\s*</{tag}>"
   match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
   return match.group(1).strip() if match else None


def IMAC(VLM, place, id, benchmark, mistake_type, t, exp, input_type, current_subtask, current_subtask_step, STL_path):

   # load the original instruction
   if input_type == 'instruction':
      mapping = {
         'a': 'MIa',
         'n': 'MIn',
         'v': 'MIv',
         'f': 'instruction'
      }
      instruction_key = mapping.get(mistake_type)
      with open(f"{benchmark}/{place}_{id}/info.json", 'r') as f:
         instruction = json.load(f)[instruction_key]

   elif input_type == 'STL':
      instruction = current_subtask
      
   else:
      print('[ERROR] Invalid input type in IMAC.')
      sys.exit(1)
   
   # VLM
   system_prompt = """
You are an expert in Vision-and-Language Navigation (VLN) for guiding an agricultural robot. Your task is to carefully read the given instruction and observe the given camera image, then think whether this instruction has evident mistakes. If no, output 'None.' in the <mistake> tag; If yes, output the mistaken word or span in the <mistake> tag, and output the corrected version in the <corrected_instruction> tag. Besides, provide a brief decision summary explaining the judgment based on the instruction and the current visual evidence.

You must follow two principles:
- Conservative Verification: Only identify a mistake if you are highly confident that the instruction is incorrect and would likely cause navigation failure or unsafe behavior, based on the instruction and the current camera observation, which reflects only the robot's present viewpoint and may not include all relevant landmarks.
- Minimal Intervention: If an error exists, identify the smallest incorrect word or span, and correct it with the minimal necessary change only. Do not perform stylistic improvements or rephrasing.

Input format:
<image> {camera image} </image>
<instruction> {original instruction} </instruction>

Output format (if no mistakes exist):
<mistake> None. </mistake>
<decision_summary> ... </decision_summary>

Output format (if mistakes exist):
<mistake> {mistaken content} </mistake>
<corrected_instruction> {corrected instruction} </corrected_instruction>
<decision_summary> ... </decision_summary>
"""

   user_prompt = f"""<instruction> {instruction} </instruction>"""
   user_image = f"{benchmark}/{place}_{id}/frames/frame_{t}.jpg"

   messages = [
      {
         'role': 'system',
         'content': system_prompt
      },
      {
         'role': 'user',
         'content': user_prompt,
         'images': [user_image]
      }
   ]
   response = ollama.chat(model=VLM, messages=messages)
   message = response['message']['content']

   # extract
   mistake = extract_tag(message, 'mistake')
   decision_summary = extract_tag(message, 'decision_summary')

   # save - instruction type
   if input_type == 'instruction':
      if mistake in ("None", "None."):
         print('[INFO] No mistake.')
         IMAC_output = {
            "mistake": "None.",
            "decision_summary": decision_summary
         }
      else:
         print(f'[INFO] Mistake: {mistake}.')
         corrected_instruction = extract_tag(message, 'corrected_instruction')
         IMAC_output = {
            "mistake": mistake,
            "corrected_instruction": corrected_instruction,
            "decision_summary": decision_summary
         }
      IMAC_instruction_path = f"runs/{exp}/{place}_{id}/IMAC_instruction.json"
      with open(IMAC_instruction_path, "w", encoding="utf-8") as f:
         json.dump(IMAC_output, f, ensure_ascii=False, indent=2)
      print(f'[INFO] IMAC instruction is saved.')

   # save - STL type
   elif input_type == 'STL':
      if mistake in ("None", "None."):
         print('[INFO] No mistake.')
         IMAC_output = {
            "time_step": t,
            "mistake": mistake,
            "subtask": instruction,
            "decision_summary": decision_summary
         }
      else:
         print(f'[INFO] Mistake: {mistake}.')
         corrected_instruction = extract_tag(message, 'corrected_instruction')

         # update STL
         with open(STL_path, "r", encoding="utf-8") as f:
            stl = json.load(f)
         for item in stl:
            if item.get("step") == current_subtask_step:
               item["subtask"] = corrected_instruction
               break
         with open(STL_path, "w", encoding="utf-8") as f:
            json.dump(stl, f, ensure_ascii=False, indent=2)
         print(f'[INFO] IMAC STL is updated.')

         IMAC_output = {
            "time_step": t,
            "mistake": mistake,
            "original_subtask": instruction,
            "corrected_subtask": corrected_instruction,
            "decision_summary": decision_summary
         }
      
      # save as json
      IMAC_STL_path = f"runs/{exp}/{place}_{id}/IMAC_STL.json"
      if os.path.exists(IMAC_STL_path):
         with open(IMAC_STL_path, "r", encoding="utf-8") as f:
            l = json.load(f)
      else:
         l = []
      l.append(IMAC_output)
      with open(IMAC_STL_path, "w", encoding="utf-8") as f:
         json.dump(l, f, ensure_ascii=False, indent=2)
      print(f'[INFO] IMAC STL is saved.')
   
   else:
      print('[ERROR] Invalid input type in IMAC.')
      sys.exit(1)
   
   return None
