import gradio as gr

model_name = 'THUDM/chatglm-6b-int4'
debug = False

if debug:

    def load_model():
        pass

    def inference(input, max_length, top_p, temperature, history=None):
        import random
        sample_outputs = [
            '我是杨开心。',
            '我两岁半了。',
            '我喜欢吃雪糕。',
        ]
        one_output = random.choice(sample_outputs)
        for i in range(len(one_output)):
            yield one_output[:i + 1]
else:
    from chatglm.modeling_chatglm import ChatGLMForConditionalGeneration
    from chatglm.tokenization_chatglm import ChatGLMTokenizer
    tokenizer = ChatGLMTokenizer.from_pretrained(model_name, trust_remote_code=True, resume_download=True)
    model = ChatGLMForConditionalGeneration.from_pretrained(
        model_name, trust_remote_code=True, resume_download=True).half().cuda()

    model = model.eval()

    def inference(input, max_length, top_p, temperature, history=None):
        if history is None:
            history = []
        for response, history in model.stream_chat_continue(tokenizer, input, history, max_length=max_length,
                                                            top_p=top_p, temperature=temperature):
            yield response


def predict(query, max_length, top_p, temperature, history):
    if history is None:
        history = []
    history.append((query, ""))
    for response in inference(query, max_length, top_p, temperature, history):
        history[-1] = (history[-1][0], response)
        yield history, ''


def predict_continue(query, latest_message, max_length, top_p, temperature, history):
    if history is None:
        history = []
    history.append((query, latest_message))
    for response in inference(query, max_length, top_p, temperature, history):
        history[-1] = (history[-1][0], response)
        yield history, '', ''


def revise(history, latest_message):
    history[-1] = (history[-1][0], latest_message)
    return history, ''


def revoke(history):
    if len(history) >= 1:
        history.pop()
    return history


MAX_TURNS = 20
MAX_BOXES = MAX_TURNS * 2

with gr.Blocks(css=""".message {
    width: inherit !important;
    padding-left: 20px !important;
}""") as demo:
    gr.Markdown(
        f"""
# 💡Creative ChatGLM WebUI

👋 欢迎来到 ChatGLM 创意世界！[https://github.com/ypwhs/CreativeChatGLM](https://github.com/ypwhs/CreativeChatGLM)

当前模型：{model_name}

* 📖 你可以使用“续写”按钮帮 ChatGLM 想一个开头，并让它继续生成更多的内容。
* 📝 你可以使用“修订”按钮修改最后一句 ChatGLM 的回复。
""")
    with gr.Row():
        with gr.Column(scale=4):
            chatbot = gr.Chatbot(elem_id="chat-box", show_label=False).style(height=800)
        with gr.Column(scale=1):
            with gr.Row():
                max_length = gr.Slider(32, 4096, value=2048, step=1.0, label="Maximum length", interactive=True)
                top_p = gr.Slider(0.01, 1, value=0.7, step=0.01, label="Top P", interactive=True)
                temperature = gr.Slider(0.01, 5, value=0.95, step=0.01, label="Temperature", interactive=True)
            with gr.Row():
                query = gr.Textbox(show_label=False, placeholder="Prompts", lines=4).style(container=False)
                generate_button = gr.Button("生成")
            with gr.Row():
                continue_message = gr.Textbox(
                    show_label=False, placeholder="Continue message", lines=2).style(container=False)
                continue_btn = gr.Button("续写")
                revise_message = gr.Textbox(
                    show_label=False, placeholder="Revise message", lines=2).style(container=False)
                revise_btn = gr.Button("修订")
                revoke_btn = gr.Button("撤回")

    history = gr.State([])
    generate_button.click(predict, inputs=[query, max_length, top_p, temperature, history], outputs=[chatbot, query])
    revise_btn.click(revise, inputs=[history, revise_message], outputs=[chatbot, revise_message])
    revoke_btn.click(revoke, inputs=[history], outputs=[chatbot])
    continue_btn.click(
        predict_continue,
        inputs=[query, continue_message, max_length, top_p, temperature, history],
        outputs=[chatbot, query, continue_message])
demo.queue().launch(server_name='0.0.0.0', server_port=7860, share=False, inbrowser=False)
