import base64, time

import streamlit as st
import streamlit_antd_components as sac
from streamlit_feedback import streamlit_feedback

import google.generativeai as genai

from database.general import Appliances, ServiceGuides
from inference.chatbot import ServiceEngineerChatbot


st.set_page_config(
    page_title="LogIQ Chatbot",
    page_icon="assets/favicon/logiq_favicon.png",
    initial_sidebar_state="expanded",
    layout="wide",
)

st.markdown(
    """
        <style>
               .block-container {
                    padding-top: 3rem;
                    padding-bottom: 0.1rem;
                }
        </style>
        """,
    unsafe_allow_html=True,
)

if "cache_model_number" not in st.session_state:
    st.session_state.cache_model_number = None

if "flag_use_context_cache" not in st.session_state:
    st.session_state.flag_use_context_cache = None

if "service_guide" not in st.session_state:
    st.session_state.service_guide = None


def set_cache_model_number(brand, sub_category, model_number):
    st.session_state.cache_model_number = model_number
    st.session_state.cache_brand = brand
    st.session_state.cache_sub_category = sub_category


@st.cache_data(ttl="60 minutes", show_spinner=False)
def build_context_cache(input_brand, input_sub_category, input_model_number):
    service_guide_db = ServiceGuides()
    (
        service_guide_title,
        path_to_service_guide,
    ) = service_guide_db.fetch_guides_by_model_number(input_model_number)

    service_engineer_chatbot = ServiceEngineerChatbot()
    context_aware_model = service_engineer_chatbot.construct_cache_model(
        input_brand,
        input_sub_category,
        input_model_number,
        service_guide_title,
        path_to_service_guide,
    )

    return context_aware_model


if __name__ == "__main__":
    with st.sidebar:
        selected_menu_item = sac.menu(
            [
                sac.MenuItem(
                    "LogIQ Chatbot",
                    icon="grid",
                ),
                sac.MenuItem(" ", disabled=True),
                sac.MenuItem(type="divider"),
            ],
            open_all=True,
        )

    if selected_menu_item == "LogIQ Chatbot":
        with st.sidebar:
            appliances_db = Appliances()

            if not st.session_state.cache_model_number:
                available_categories = appliances_db.fetch_all_categories()
                input_sub_category = st.selectbox(
                    "Select Appliance",
                    available_categories,
                    index=None,
                    placeholder="Select Appliance",
                    label_visibility="collapsed",
                )

                available_brands = appliances_db.fetch_brands_by_sub_category(
                    input_sub_category
                )
                input_brand = st.selectbox(
                    "Select the Brand",
                    available_brands,
                    index=None,
                    placeholder="Select the Brand",
                    label_visibility="collapsed",
                )

                available_models = appliances_db.fetch_models_by_brand_and_sub_category(
                    input_brand, input_sub_category
                )
                input_model_number = st.selectbox(
                    "Select the Model",
                    available_models,
                    index=None,
                    placeholder="Select the Model",
                    label_visibility="collapsed",
                )

                if st.button(
                    "🛠️ Configure Chatbot",
                    use_container_width=True,
                    disabled=not (input_model_number),
                ):
                    set_cache_model_number(
                        input_brand, input_sub_category, input_model_number
                    )
                    st.rerun()

                st.markdown("<BR>" * 7, unsafe_allow_html=True)
                with st.popover("Acknowledgement", use_container_width=True):
                    st.success(
                        "Google Cloud credits are provided for this project! #AISprint"
                    )

        if st.session_state.cache_model_number:
            if "messages" not in st.session_state:
                st.session_state.messages = []

            for message in st.session_state.messages:
                with st.chat_message(message["role"]):
                    st.markdown(message["content"])

            if "gemini_flash" not in st.session_state:
                st.toast(
                    f"Configuring chatbot for {st.session_state.cache_model_number}. This may take a minute."
                )

                with open("assets/preloaders/work_in_progress.gif", "rb") as f:
                    image_data = f.read()
                    encoded_image = base64.b64encode(image_data).decode()

                    st.write(" ")
                    preloader_work_in_progress = st.markdown(
                        f'<BR><BR><div class="rounded-image"><img src="data:image/png;base64,{encoded_image}"></div>',
                        unsafe_allow_html=True,
                    )

                with preloader_work_in_progress:
                    configuration_information = f"""
                    Configuring chatbot for
                    {st.session_state.cache_brand} {st.session_state.cache_sub_category} ({st.session_state.cache_model_number})
                    """
                    warning_configuring_chatbot = st.sidebar.warning(
                        configuration_information, icon="🛠️"
                    )

                    try:
                        st.session_state.gemini_flash = build_context_cache(
                            st.session_state.cache_brand,
                            st.session_state.cache_sub_category,
                            st.session_state.cache_model_number,
                        )
                        st.session_state.flag_use_context_cache = True

                    except Exception as error:
                        service_guide_db = ServiceGuides()
                        (
                            service_guide_title,
                            path_to_service_guide,
                        ) = service_guide_db.fetch_guides_by_model_number(
                            st.session_state.cache_model_number
                        )

                        service_engineer_chatbot = ServiceEngineerChatbot()
                        st.session_state.service_guide = (
                            service_engineer_chatbot.post_service_guide_to_gemini(
                                service_guide_title, path_to_service_guide
                            )
                        )

                        st.session_state.gemini_flash = (
                            service_engineer_chatbot.construct_flash_model(
                                st.session_state.cache_brand,
                                st.session_state.cache_sub_category,
                                st.session_state.cache_model_number,
                            )
                        )
                        st.session_state.flag_use_context_cache = False

                    warning_configuring_chatbot.empty()

            if st.session_state.cache_model_number:
                with st.sidebar.container(height=405, border=False):
                    configuration_information = f"""
                    Chatbot configured for
                    {st.session_state.cache_brand} {st.session_state.cache_sub_category} ({st.session_state.cache_model_number})
                    """
                    st.success(configuration_information, icon="🛠️")

                    service_guide_db = ServiceGuides()
                    (
                        service_guide_title,
                        path_to_service_guide,
                    ) = service_guide_db.fetch_guides_by_model_number(
                        st.session_state.cache_model_number
                    )

                    st.download_button(
                        label=f"📄 Download Service Guide",
                        data=open(path_to_service_guide, "rb").read(),
                        file_name=f"{service_guide_title}.pdf",
                        use_container_width=True,
                    )

                if st.sidebar.button(
                    "⚙️ Clear and Reconfigure", use_container_width=True
                ):
                    del st.session_state.cache_model_number
                    del st.session_state.cache_brand
                    del st.session_state.cache_sub_category

                    del st.session_state.messages
                    del st.session_state.chat
                    del st.session_state.service_guide

                    del st.session_state.gemini_flash
                    del st.session_state.flag_use_context_cache

                    st.rerun()

            if "chat" not in st.session_state:
                st.session_state.chat = st.session_state.gemini_flash.start_chat(
                    history=st.session_state.messages
                )

                welcome_message = f"""
                Hello there! I am your virtual assistant, LogIQ.

                I'm ready to assist you with questions on {st.session_state.cache_brand} {st.session_state.cache_sub_category} (Model: {st.session_state.cache_model_number}).  I can help you troubleshoot issues, replace parts, and offer useful maintenance tips to keep your appliance running smoothly.
                
                What can I do for you today to make sure your appliance works at its best?
                """
                st.session_state.messages.append(
                    {
                        "role": "assistant",
                        "content": welcome_message,
                    }
                )
                st.rerun()

            if prompt := st.chat_input("Type your question here..."):
                st.session_state.messages.append({"role": "user", "content": prompt})

                with st.chat_message("user"):
                    st.markdown(prompt)

                with st.chat_message("assistant"):
                    with st.spinner(
                        "Thinking... (Please wait 15-20 seconds for the chatbot to respond to your query.)"
                    ):
                        if st.session_state.flag_use_context_cache == True:
                            response_from_model = st.session_state.chat.send_message(
                                [(prompt)],
                            )
                        else:
                            response_from_model = st.session_state.chat.send_message(
                                [st.session_state.service_guide, prompt]
                            )

                        def response_generator(response):
                            for word in response:
                                time.sleep(0.05)
                                try:
                                    yield word.text
                                except Exception as err:
                                    yield word

                        try:
                            response = st.write_stream(
                                response_generator(response_from_model)
                            )

                        except Exception as err:
                            fallback_message = (
                                f"Sorry, I am unable to answer this.\nReason: {err}"
                            )

                            response = st.write_stream(
                                response_generator(fallback_message)
                            )

                st.session_state.messages.append(
                    {"role": "assistant", "content": response}
                )

        else:
            st.markdown(
                "<BR><BR><H2>LogIQ - Service Engineer Chatbot ⛑️</H2>",
                unsafe_allow_html=True,
            )
            st.markdown(
                "<H4>Diagnose, Troubleshoot, and Repair White Label Appliances with Expert Precision!</H4>Facing an issue with your kitchen appliance, but not sure whom to call? Or perhaps you need immediate assistance with a repair? Simply describe your problem, and our chatbot powered by Gemini 1.5 will help you troubleshoot these problems in a single tap!",
                unsafe_allow_html=True,
            )

            st.markdown("<BR>", unsafe_allow_html=True)
            usage_instructions = """
            **Here's how you can get started:**

            1. Simply select the brand and model of your appliance, and type in the issues you're facing or the specific service you need.
            2. Wait for the chatbot to analyze the service manuals/guides and provide expert advice and troubleshooting tips right away.
            """
            st.info(usage_instructions)
