import gradio as gr; from lifeos.envs.student_week_openenv import StudentWeekEnv
def run():
     try:
           e = StudentWeekEnv(); o, i = e.reset(); return str(o)
    except Exception as x: return str(x)
demo = gr.Interface(fn=run, inputs=None, outputs="text"); demo.launch()
