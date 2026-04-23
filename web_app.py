import os
import sys
import gradio as gr

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from lifeos.envs.student_week_openenv import LifeOSGymEnv

def run_episode():
        try:
                    env = LifeOSGymEnv()
                    obs, info = env.reset()
                    return "Simulation started. Obs: " + str(obs)
except Exception as e:
        return f"Error: {str(e)}"

with gr.Blocks() as demo:
        gr.Markdown("# LifeOS Demo")
        run_btn = gr.Button("Run Episode")
        output = gr.Textbox()
        run_btn.click(run_episode, outputs=output)

    if __name__ == "__main__":
            demo.launch()
        