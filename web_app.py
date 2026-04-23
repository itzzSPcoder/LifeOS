import gradio as gr
from lifeos.envs.student_week_openenv import LifeOSGymEnv
def run():
      try:
              env = LifeOSGymEnv()
              obs, info = env.reset()
              return str(obs)
    except Exception as e:
            return str(e)
demo = gr.Interface(fn=run, inputs=None, outputs="text")
demo.launch()
