import os, sys, gradio as gr; from lifeos.envs.student_week_openenv import LifeOSGymEnv
def run_episode():
     try:
           env = LifeOSGymEnv(); obs, info = env.reset(); return "Started. Obs: " + str(obs)
except Exception as e: return f"Error: {str(e)}"
with gr.Blocks() as demo:
     gr.Markdown("# LifeOS Demo"); run_btn = gr.Button("Run Episode"); output = gr.Textbox(); run_btn.click(run_episode, outputs=output)
    if __name__ == "__main__": demo.launch()
