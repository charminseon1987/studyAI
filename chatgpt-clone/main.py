# import streamlit as st 
# import time

# st.header("hello SS ")

# st.button("Click me please!!")

# st.text_input(
#     "Write you API Key",
#     max_chars = 200
#     )


# st.feedback("faces")



# with st.sidebar:
#     st.badge("Badge 1 ")


# tab1, tab2, tab3 = st.tabs(["Agent","Chat","Output"])

# with tab1: 
#     st.header("Agent")
#     st.button("click")


# with tab2:
#     st.header("Agent2")



# with tab3:
#     st.header("Agent3")


# with st.chat_message('ai'):
#     st.text('Hello!!!')
#     with st.status("Agent is using tool") as status:
#         time.sleep(1)
#         status.update(label="Agent is searching the web...")
#         time.sleep(2)
#         status.update(label="Agent is reading page...")
#         time.sleep(3)
#         status.update(state = "complete")

# with st.chat_message('human'):
#     st.text("Hi!!!!")


# st.chat_input("Write a message for the assistant...",accept_file=True,)
# ==============

import streamlit as st 

st.header("Hello *^----------^*")
name = st.text_input("What is your name?")
st.write(f"hello {name}")


