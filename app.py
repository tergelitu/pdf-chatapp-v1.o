import streamlit as st
import os
from dotenv import load_dotenv
from PyPDF2 import PdfReader
from streamlit_extras.add_vertical_space import add_vertical_space
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.embeddings.openai import OpenAIEmbeddings
from langchain.vectorstores import FAISS
from langchain_community.chat_models import ChatOpenAI
from langchain.chains.question_answering import load_qa_chain
from langchain.chains import ConversationalRetrievalChain
from langchain.memory import ConversationBufferMemory
from langchain.callbacks import get_openai_callback
from langchain.schema.document import Document
from langchain.chains.summarize import load_summarize_chain

# Sidebar UI
st.markdown(
    """
    <style>
    [data-testid="stSidebar"] {
        background-color: #000000;
    }
    [data-testid="stSidebar"] * {
        color: #2196F3 !important;
    }
    .block-container, .stTextInput label, .stFileUploader label, .stRadio label, .stSlider label, .stSelectbox label, .stExpanderHeader, .stButton, .stDownloadButton, .stCaption, .stCheckbox label {
    color: #42a5f5 !important; /* Lighter blue */
    }
    </style>
    """,
    unsafe_allow_html=True
)

with st.sidebar:
    st.title('PDF Chat App')
    st.markdown('''
    This app lets you:
    - Chat with a PDF using AI
    - View sources and follow-up Qs
    - Summarize documents instantly
    ''')
    add_vertical_space(5)
    st.write('Made with ❤️ by [Tergel](https://github.com/tergelitu)')

# Main function
def main():
    st.markdown('<div class="gradient-bg"></div>', unsafe_allow_html=True)
    st.markdown("<h1 style='color:#42a5f5;'>Chat with PDF</h1>", unsafe_allow_html=True)

    load_dotenv()
    st.markdown("<span style='color:#42a5f5; font-weight:bold; font-size:18px;'>📄 Upload your PDF</span>", unsafe_allow_html=True)
    pdf = st.file_uploader("", type='pdf')

    if pdf is not None:
        with st.expander("📑 Preview PDF Text"):
            reader = PdfReader(pdf)
            text = ""
            documents = []
            for i, page in enumerate(reader.pages):
                page_text = page.extract_text()
                if page_text:
                    text += f"\n\n--- Page {i+1} ---\n\n{page_text}"
                    documents.append(Document(page_content=page_text, metadata={"page": i + 1}))
            st.text_area("Extracted Text", value=text[:2000] + '...' if len(text) > 2000 else text, height=300)

        with st.spinner("🔍 Processing PDF..."):
            text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=150)
            chunks = text_splitter.split_documents(documents)
            store_name = pdf.name[:-4]

            if os.path.exists(f"{store_name}"):
                vectorstore = FAISS.load_local(
                    f"{store_name}",
                    OpenAIEmbeddings(),
                    allow_dangerous_deserialization=True
                )
            else:
                embeddings = OpenAIEmbeddings()
                vectorstore = FAISS.from_documents(chunks, embedding=embeddings)
                vectorstore.save_local(f"{store_name}")

        if st.button("🧠 Summarize PDF"):
            with st.spinner("Generating summary..."):
                llm = ChatOpenAI(temperature=0, model='gpt-3.5-turbo')
                summary_chain = load_summarize_chain(llm, chain_type="map_reduce")
                summary = summary_chain.run(chunks)
                st.success("Summary:")
                st.markdown(f"📝 {summary}")

        st.markdown("---")
        st.subheader("💬 Chat with your PDF")

        memory = ConversationBufferMemory(memory_key="chat_history", return_messages=True, output_key="answer")
        retriever = vectorstore.as_retriever(search_kwargs={"k": 3})
        qa_chain = ConversationalRetrievalChain.from_llm(
            ChatOpenAI(temperature=0, model="gpt-3.5-turbo"),
            retriever=retriever,
            memory=memory,
            return_source_documents=True,
            output_key="answer"
        )

        user_query = st.text_input("Ask a question")

        if user_query:
            with st.spinner("🤖 Thinking..."):
                with get_openai_callback() as cb:
                    result = qa_chain({"question": user_query})
                    answer = result['answer']
                    sources = result.get('source_documents', [])
                    print(cb)

            st.markdown(f"""
            <div class="chat-bubble user"><b>You:</b> {user_query}</div>
            <div class="chat-bubble bot"><b>Bot:</b> {answer}</div>
            """, unsafe_allow_html=True)

            if sources:
                st.markdown("📚 **Sources:**")
                for doc in sources:
                    page_num = doc.metadata.get('page', '?')
                    snippet = doc.page_content[:300]
                    st.markdown(f"- Page {page_num}: `{snippet}...`")

            st.markdown("💡 **Follow-up Suggestions**")
            col1, col2, col3 = st.columns(3)
            with col1:
                if st.button("Explain more"):
                    st.session_state["follow_up"] = f"Explain more about: {user_query}"
            with col2:
                if st.button("Summarize"):
                    st.session_state["follow_up"] = f"Summarize this topic: {user_query}"
            with col3:
                if st.button("Any examples?"):
                    st.session_state["follow_up"] = f"Give examples related to: {user_query}"

            if "follow_up" in st.session_state:
                follow_query = st.session_state.pop("follow_up")
                with st.spinner("📘 Generating follow-up..."):
                    result = qa_chain({"question": follow_query})
                    st.markdown(f"""
                    <div class="chat-bubble user"><b>You:</b> {follow_query}</div>
                    <div class="chat-bubble bot"><b>Bot:</b> {result['answer']}</div>
                    """, unsafe_allow_html=True)

    # Footer
    st.markdown("""
        <hr style="border: 1px solid #2196F3;">
        <div style='text-align: center; color: #42a5f5; font-size: 14px;'>
            Made with ❤️ by <a href='https://github.com/tergelitu' target='_blank' style='color: #64b5f6;'>Tergel</a>
        </div>
    """, unsafe_allow_html=True)

if __name__ == '__main__':
    main()

# Gradient Background and Chat Bubbles CSS
st.markdown(
    """
    <style>
    .gradient-bg {
        position: fixed;
        top: 0;
        left: 0;
        width: 100vw;
        height: 100vh;
        z-index: -1;
        background: linear-gradient(135deg, #000000 0%, #0d47a1 100%);
        animation: gradientMove 30s ease infinite;
    }

    @keyframes gradientMove {
        0% { background-position: 0% 50%; }
        50% { background-position: 100% 50%; }
        100% { background-position: 0% 50%; }
    }

    .chat-bubble {
        border-radius: 15px;
        padding: 12px;
        margin: 10px 0;
        max-width: 90%;
        font-size: 16px;
        line-height: 1.5;
    }
    .user {
        background-color: #1565c0;
        color: white;
        margin-left: auto;
        text-align: right;
    }
    .bot {
        background-color: #1e88e5;
        color: white;
        margin-right: auto;
        text-align: left;
    }

    .stApp {
        background-color: transparent !important;
    }
    </style>
    """,
    unsafe_allow_html=True
)
