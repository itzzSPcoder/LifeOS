import gradio as gr; from lifeos.envs.student_week_openenv import StudentWeekEnv
def run(): return str(StudentWeekEnv().reset())
demo = gr.Interface(fn=run, inputs=None, outputs="text"); demo.launch()
