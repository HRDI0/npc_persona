import streamlit as st
import time
st.set_page_config(page_title = "persona chat")
st.title("persona_chat")

if "messages" not in st.session_state:
    st.session_state.messages = []

for message in st.session_state.messages:
    with st.chat_message(messsage["role"]):
        st.markdown(message["content"])

def stream_response(text : str):
    '''텍스트 스트림으로 반환하는 제네레이터'''
    for char in text:
        yield char
        time.sleep(0.02)

if prompt := st.chat_input('메세지를 입력하세요'):
    st.session_state.messages.append({"role":"user",
                                        "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    response_text = f"안녕하세요! '{prompt}'에 대해 답변해드리겠습니다."

    with st.chat_message("assistant"):
        response = st.write_stream(stream_response(response_text))

    st.session_state.messages.append({"role":"assistant", "content" : response})