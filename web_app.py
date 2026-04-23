import gradio as gr
from lifeos.envs.student_week_openenv import LifeOSGymEnv
env = LifeOSGymEnv()
obs, info = env.reset()
def run():
      return str(obs)
    demo = gr.Interface(fn=run, inputs=None, outputs="text")
demo.launch()
