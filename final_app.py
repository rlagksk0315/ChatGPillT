# color code: #1C55DE
import streamlit as st
from PIL import Image
import base64
from io import BytesIO
import time
import openai
from openai import OpenAI
import requests
import re

if 'input_key' not in st.session_state:
    st.session_state.input_key = 0
if 'stage' not in st.session_state:
    st.session_state['stage'] = 'intro'  # Possible values: 'intro', 'form', 'waiting', 'chat'
if 'chat_history' not in st.session_state:
    st.session_state['chat_history'] = []
if 'age' not in st.session_state:
    st.session_state['age'] = 30
if 'pregnant' not in st.session_state:
    st.session_state['pregnant'] = False
if 'time_to_switch' not in st.session_state:
    st.session_state['time_to_switch'] = time.time() + 5
if 'session_id' not in st.session_state:
    st.session_state.session_id = str(time.time())
if 'show_chat' not in st.session_state:
    st.session_state.show_chat = False

def image_to_base64(image: Image.Image) -> str:
    buffered = BytesIO()
    image.save(buffered, format="PNG")
    return base64.b64encode(buffered.getvalue()).decode("utf-8")

OPENAI_API_KEY = "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"
client = OpenAI(api_key = OPENAI_API_KEY)

#------------------------------------------------------------------------------------------------
#식약처 의약품안전사용서비스(DUR) 품목 정보
combine_endpoint = "http://apis.data.go.kr/1471000/DURPrdlstInfoService03/getUsjntTabooInfoList03"
pregnant_endpoint ="http://apis.data.go.kr/1471000/DURPrdlstInfoService03/getPwnmTabooInfoList03"
kid_endpoint ="http://apis.data.go.kr/1471000/DURPrdlstInfoService03/getSpcifyAgrdeTabooInfoList03"
#품목정보 조회
dur_endpoint = "http://apis.data.go.kr/1471000/DURPrdlstInfoService03/getDurPrdlstInfoList03"
decoding_key = "c1Mn0Gc+QUHLiZM9/r9P5gye2iu25VyQvnRgwm7+oH/Z+Yitui6htgMV385wCOvway8T82ojxMLiZ0weZGDgog=="
#------------------------------------------------------------------------------------------------
def reform_name(item):
    reform_name = re.sub(r"\(.*?\)", "", item)
    return reform_name
#------------------------------------------------------------------------------------------------
#병용 금기 DUR response 받는 함수
def combine_resp(endpoint, params, item_output):
    #GET request
    response = requests.get(endpoint, params=params)    
    if response.status_code == 200:
        pair = {}
        item_list = []
        symptom_list = []
        response = response.json()
        
        if response['body']['totalCount'] == 0:
            return "병용 가능"
        else:
            len_response = len(response['body']['items'])
            st.write(len_response)
            for i in range(len_response):
                item = response['body']['items'][i]['MIXTURE_ITEM_NAME']
                item = reform_name(item)
                item_list.append(item)
                
                symptom = response['body']['items'][i]['PROHBT_CONTENT']
                symptom_list.append(symptom)
                
                pair[item] = symptom
            st.write(item_list)
            #item_list는 병용 금기 아이템 리스트
            if item_output in item_list:
                msg = "병용 금기. 사유 : " + pair[item_output]
                return msg
            else:
                msg = "병용 가능"
                return msg
    else:
        return "응답이 취소되었습니다. 오류코드:" + str(response.status_code)
#----------------------------------------------------------------------------------------#
#임부 금기 DUR response 받는 함수
def preg_resp(endpoint, params):
    #GET request
    response = requests.get(endpoint, params=params)
    if response.status_code == 200:
        pair = {}
        item_list = []
        symptom_list = []
        response = response.json()
        if response['body']['totalCount'] == 0:
            return "임산부 복용 가능"
        else:
            symptom = response['body']['items'][0]['PROHBT_CONTENT']
            return "임부 금기. 사유 : " + symptom
        return response
    else:
        return "응답이 취소되었습니다. 오류코드:" + str(response.status_code)
#----------------------------------------------------------------------------------------#
#특정 연령 금기 DUR response 받는 함수
def kid_resp(endpoint, params):
    #GET request
    response = requests.get(endpoint, params=params)
    
    if response.status_code == 200:
        pair = {}
        item_list = []
        symptom_list = []
        response = response.json()
        if response['body']['totalCount'] == 0:
            return "아이 복용 가능"
        else:
            symptom = response['body']['items'][0]['PROHBT_CONTENT']
            return "아이 금기. 사유 : " + symptom
    else:
        return "응답이 취소되었습니다. 오류코드:" + str(response.status_code)
#----------------------------------------------------------------------------------------#
def get_dur(question_type, item_name):
    endpoint = ""
    #질문 유형에 따라 endpoint를 할당한다.
    if question_type == "병용가능":
        endpoint = combine_endpoint
        #st.write(item_name.split(","))
        item_input = item_name.split(",")[0]
        item_output = item_name.split(",")[1]

        #응답받을 parameter
        params = {
        'serviceKey': decoding_key,  
        'type' : "json",
        'itemName': item_input
        }
        raw_message = combine_resp(endpoint, params, item_output)
        return raw_message

    elif question_type == "아이":
        endpoint = kid_endpoint

        #응답받을 parameter
        params = {
        'serviceKey': decoding_key,  
        'type' : "json",
        'itemName': item_name
        }
        raw_message = kid_resp(endpoint, params)
        return raw_message
        
    elif question_type == "임신":
        endpoint = pregnant_endpoint
        #응답받을 parameter
        params = {
        'serviceKey': decoding_key,  
        'type' : "json",
        'itemName': item_name
        }
        raw_message = preg_resp(endpoint, params)
        return raw_message

    


#-------------------------------------------------------------------------------
parser_instruct = """
너는 문장에서 문장에서 키워드를 추출하는 AI 어시스턴트야.
질문에 대한 답변 말고 문장에서 어떤 종류의 질문인지랑 약 이름만 추출하면 돼.
질문의 종류는 다음과 같고 다른 질문 종류는 없어.

-임신
-아이
-병용가능

Q: 세나진정 임신한 사람에게 사용해도 될까?
A: 임신,세나진정

Q: 하트만액_ 아이에게 사용해도 될까?
A: 아이,하트만액

Q: 옴니파큐랑 시타폴엠정이랑 같이 써도 돼?
A: 병용가능,옴니파큐,시타폴엠정
"""

medical_prompt = """
너는 대학병원에서 일하는 의사이자 약사야.
환자가 의약품에 대해서 질문하면 친절하게 답변해줘.
환자의 질문 유형은 다음 세개가 전부야. 
- 병용 금기
- 임산부 금기
- 유아 금기
답변의 근거는 대한민국 DUR 정보이고
만약 다른 종류의 질문을 한다면 그부분에 대해서는 잘 모른다고 답변해줘.
"""

dur_prompt = """
너는 대학병원에서 일하는 친절한 의사이자 약사야.
대한민국 DUR 정보가 담긴 문자열과 환자의 질문을 전달할거야. 

환자가 의약품에 대해서 질문하면 DUR 정보를 기반으로 친절하게, 자세하게 답변해줘.
환자의 질문 유형은 다음 세개가 전부야. 
- 병용 금기
- 임산부 금기
- 유아 금기

답변 규칙
- DUR 정보에 내용이 없는 경우 금기사항이 아니라고 답변.
- 금기사항일 경우 금기 사유를 확인하고 답변
- 반드시 한번만에 답변
"""

def get_openai_response(message):
    #parsing해서 질문 유형과 의약품 이름을 얻는다.
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": parser_instruct},
            {"role": "user", "content": message}
        ]
    )
    bot_resp = response.choices[0].message.content
    target = bot_resp.split(',')
    question_type = target[0]

    # 병용가능에서는 약이 2가지이므로 split에서 두개로 나뉜 문자열을 하나의 문자열로 다시 합친다.
    if question_type == "병용가능":
        item_name = target[1] + "," + target[2]
    else:
        item_name = target[1]

    dur_resp = get_dur(question_type,item_name)
    final_msg = "DUR 정보:\n" + dur_resp + "\n" + "환자의 질문: " + message

    #DUR정보 기반으로 답변을 얻는다.    
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": dur_prompt},
            {"role": "user", "content": final_msg}
        ],
        temperature = 0.5
    )
    return response.choices[0].message.content
#---------------------------------------------------------------------------------------
logo_path = './logo.png'
logo_image = Image.open(logo_path)
dr_icon_path = './dr_icon.png'
dr_icon_image = Image.open(dr_icon_path)
patient_icon_path = './patient_icon.png'
patient_icon_image = Image.open(patient_icon_path)

dr_icon_base64 = image_to_base64(dr_icon_image)
patient_icon_base64 = image_to_base64(patient_icon_image)

st.set_page_config(page_title='ChatGPillT', page_icon=':pill:')

col1, col2, col3 = st.columns([1, 2, 1])
with col1:
    st.write("")
with col2:
    st.image(logo_image)
with col3:
    st.write("")

chat_bubble_css = """
<style>
    .chat-bubble {
        padding: 10px;
        border-radius: 25px;
        border: 2px solid #1C55DE;
        margin: 10px;
        position: relative;
        background-color: white;
        display: flex;
        align-items: center;
        font-size: 16px; /* Adjust the font size as needed */
    }
    .chat-bubble-icon {
        width: 40px; /* Adjust the width as needed */
        height: 40px; /* Adjust the height as needed */
        margin-right: 10px;
    }
    .chat-bubble-text {
        flex: 1;
    }
    .chat-bubble:after {
        content: "";
        position: absolute;
        bottom: -20px; /* position it outside of the bubble */
        left: 50%;
        border: 10px solid transparent;
        border-top-color: white;
        border-bottom: 0;
        margin-left: -10px;
        transform: translateX(-50%); /* ensures that it's centered under the bubble */
    }
</style>
"""

# Introductory text and START CHAT button
if st.session_state['stage'] == 'intro':

    st.markdown("""
        <div style='text-align: center;'>
            <p style='font-size: 20px;'><strong style='color: #1C55DE;'>ChatG<em>Pill</em>T</strong>는 <strong>의약품 정보를 제공하는 챗봇</strong>으로,</p>
            <p style='font-size: 20px;'>이와 함께라면 평소 의약품에 관하여 갖고 있었던</p>
            <p style='font-size: 20px;'>궁금증을 모두 풀어볼 수 있습니다!</p>
        </div>
        """, unsafe_allow_html=True)

    col1, col2, col3, col4, col5 = st.columns([1, 1, 2, 1, 1])
    with col3:
        
        st.markdown(f"""
            <style>
                div.stButton > button {{
                    background-color: #1C55DE;
                    color: white;
                    border-radius: 5px;
                    border: none;
                    padding: 0.75rem 3rem;  # Reduced padding to fit the text
                    font-size: 18px;  # Slightly reduced font-size
                    display: block;
                    width: 100%;
                    text-align: center;
                }}
            </style>""", unsafe_allow_html=True)

        if st.button('💬 START CHAT'):
            st.session_state['stage'] = 'form'
            st.experimental_rerun()


def handle_submit():
    st.session_state['age'] = st.session_state.age
    st.session_state['pregnant'] = st.session_state.pregnant
    #st.session_state['stage'] = 'waiting'
    st.session_state['show_dr_response'] = True  # New flag to show Dr. Pill's message
    #st.session_state['time_to_switch'] = time.time() + 2 
    st.session_state.show_chat = False 

# User inputs for age and pregnancy status
if st.session_state['stage'] == 'form':

    st.markdown(chat_bubble_css, unsafe_allow_html=True)
    st.markdown(f"""
        <div class="chat-bubble">
            <img class="chat-bubble-icon" src="data:image/png;base64,{dr_icon_base64}" alt="Dr. Pill icon">
            <div class="chat-bubble-text">
                <strong>Dr. Pill</strong>: '안녕하세요! 본인의 상태에 해당되는 것을 체크해주시면, 의약품에 대한 더 정확한 정보를 제공해드릴 수 있습니다 :)'
            </div>
        </div>
        """, unsafe_allow_html=True)

    # Create input elements for age and pregnancy status
    age = st.slider('나이', 0, 100, 30)  # Age slider
    pregnant = st.checkbox('임신 O')  # Pregnancy checkbox
    not_pregnant = st.checkbox('임신 X')  # Non-pregnancy checkbox

    st.markdown(f"""
        <style>
            div.stButton > button {{
                background-color: #1C55DE;
                color: white;
                border-radius: 5px;
                border: none;
                padding: 0.75rem 3rem;  # Reduced padding to fit the text
                font-size: 18px;  # Slightly reduced font-size
                display: block;
                width: 100%;
                text-align: center;
            }}
        </style>""", unsafe_allow_html=True)

    if st.button('Submit'):
        handle_submit()
        st.session_state['stage'] = 'chat'
        st.experimental_rerun()

# Dr. Pill's message
if st.session_state.get('show_dr_response', False):
    st.markdown(chat_bubble_css, unsafe_allow_html=True)
    st.markdown(f"""
        <div class="chat-bubble">
            <img class="chat-bubble-icon" src="data:image/png;base64,{dr_icon_base64}" alt="Dr. Pill icon">
            <div class="chat-bubble-text"><strong>Dr. Pill</strong>: 감사합니다! 이제 채팅으로 바로 도와드리도록 하겠습니다.</div>
        </div>
    """, unsafe_allow_html=True)
    
    st.session_state['show_dr_response'] = False
    st.session_state.show_chat = True
    # Rerun to move on to the chat stage
    st.experimental_rerun()


# CHAT
chat_interface_css = """
<style>
.user-bubble {
    justify-content: flex-end;
    text-align: right;
}

.dr-bubble {
    justify-content: flex-start;
    text-align: left;
}

.chat-bubble-icon {
    width: 30px; /* Smaller icon size */
    height: 30px; /* Smaller icon size */
}

.user-message {
    background-color: #1C55DE;
    color: white;
}

.dr-message {
    background-color: white;
    color: black;
}

/* Use this to clear margins and padding for a full-width chat input */
.stTextInput > div > div > input {
    width: calc(100% - 48px); /* Adjust width considering padding and button width */
}
</style>
"""

st.markdown(chat_interface_css, unsafe_allow_html=True)

def render_chat_message(message, is_user):
    if is_user:
        bubble_class = "user-bubble user-message"
        icon = patient_icon_base64
        icon_alt = "User"
    else:
        bubble_class = "dr-bubble dr-message"
        icon = dr_icon_base64
        icon_alt = "Dr. Pill"

    st.markdown(f"""
    <div style="display: flex; flex-direction: column; align-items: {'flex-end' if is_user else 'flex-start'};">
        <div class="chat-bubble {bubble_class}" style="display: flex; align-items: center; margin-bottom: 5px;">
            <img src="data:image/png;base64,{icon}" class="chat-bubble-icon" alt="{icon_alt}" style="margin: {'0 10px 0 0' if is_user else '0 0 0 10px'};">
            <p style="padding: 10px 15px; border-radius: 15px; margin: 0;">{message}</p>
        </div>
    </div>
    """, unsafe_allow_html=True)


# with st.container():
#     col1, col2 = st.columns([5, 1], gap="small")
#     with col1:
#         user_input = st.text_input("Type your message here...", key=f"user_input_{st.session_state.input_key}", placeholder="Type your message here...")
#     with col2:
#         st.markdown("""
#             <style>
#                 div.stButton > button {
#                     width: 100%;
#                     height: 100%;
#                     padding: 0.75rem; /* Match input height */
#                 }
#             </style>
#         """, unsafe_allow_html=True)
#         if st.button('Send', key=f"send_button_{st.session_state.input_key}"):
#             # Process send action
#             pass # replace with your send message handling code

if st.session_state['stage'] == 'chat':
    
    with st.container():
        col1, col2 = st.columns([5, 1], gap="small")
        with col1:
            for chat_message in st.session_state['chat_history']:
                render_chat_message(chat_message["message"], chat_message["is_user"])
            user_input = st.text_input("메세지 입력해주세요...", key=f"user_input_{st.session_state.input_key}", placeholder="예) 아자프린정 소아 줘도 돼?")
        with col2:
            st.markdown("""
                <style>
                    div.stButton > button {
                        width: 100%;
                        height: 100%;
                        padding: 0.75rem; /* Match input height */
                    }
                </style>
            """, unsafe_allow_html=True)
            if st.button('Send', key=f"send_button_{st.session_state.input_key}"):
                if user_input:
                    # Process the user's message
                    st.session_state.chat_history.append({"message": user_input, "is_user": True})

                    if user_input == '안녕하세요!':
                        bot_response = "안녕하세요, 의약품 정보 알려주는 Dr.Pill입니다. 의약품을 복용해도 되는지 자유롭게 여쭤보시면 됩니다. 예를 들면, '아자프린정 소아 줘도 돼?' 이런 형식으로 간단하게 질문하면 됩니다."
                    else:
                        # Get the response from OpenAI
                        bot_response = get_openai_response(user_input)
                    
                    # Append the response to the chat history
                    st.session_state.chat_history.append({"message": bot_response, "is_user": False})
                    # Increment the input key to clear the input box
                    st.session_state.input_key += 1
                    # Rerun the app to update the chat
                    st.experimental_rerun()

# if st.session_state.show_chat:
#     for chat_message in st.session_state['chat_history']:
#         render_chat_message(chat_message["message"], chat_message["is_user"])

#     user_input = st.text_input(
#         "Type your message here...",
#         key=f"user_input_{st.session_state.input_key}",
#         placeholder="Type your message here..."
#     )

    # if st.button('Send', key=f"send_button_{st.session_state.input_key}"):
    #     if user_input:
    #         # Process the user's message
    #         st.session_state.chat_history.append({"message": user_input, "is_user": True})
    #         # Get the response from OpenAI
    #         bot_response = get_openai_response(user_input)
    #         # Append the response to the chat history
    #         st.session_state.chat_history.append({"message": bot_response, "is_user": False})
    #         # Increment the input key to clear the input box
    #         st.session_state.input_key += 1
    #         # Rerun the app to update the chat
    #         st.experimental_rerun()