import os
import io
import time
import json
from datetime import datetime

import firebase_admin
from firebase_admin import credentials, firestore
import pandas as pd
import plotly.express as px
import streamlit as st

# ============================================================
# 1. ИНИЦИАЛИЗАЦИЯ FIREBASE
# ============================================================
if not firebase_admin._apps:
    key_content = os.getenv("FIREBASE_KEY")

    if key_content:
        cred_dict = json.loads(key_content)
        cred = credentials.Certificate(cred_dict)
    elif os.path.exists("serviceAccountKey.json"):
        cred = credentials.Certificate("serviceAccountKey.json")
    else:
        st.error("❌ Ошибка: Ключ Firebase не найден ни в Secrets, ни в файле!")
        st.stop()

    firebase_admin.initialize_app(cred)

db = firestore.client()

st.set_page_config(page_title="Опрос: Автоматизация труда", layout="wide")

# ============================================================
# 2. КАСТОМНЫЙ CSS (неоновый стиль)
# ============================================================
st.markdown("""
<style>
    .main .block-container {
        animation: cyberEntrance 0.8s cubic-bezier(0.25, 1, 0.5, 1) forwards;
    }
    @keyframes cyberEntrance {
        0% { opacity: 0; transform: translateY(30px) scale(0.99); filter: blur(5px); }
        100% { opacity: 1; transform: translateY(0) scale(1); filter: blur(0); }
    }

    .cyber-title {
        font-weight: 700;
        animation: neonPulse 2s infinite alternate;
    }
    @keyframes neonPulse {
        0% { text-shadow: 0 0 5px rgba(99, 102, 241, 0.2), 0 0 10px rgba(99, 102, 241, 0.4); }
        100% { text-shadow: 0 0 15px rgba(236, 72, 153, 0.6), 0 0 25px rgba(236, 72, 153, 0.4); }
    }

    div[data-testid="stMetric"] {
        border: 1px solid rgba(99, 102, 241, 0.2);
        padding: 15px !important;
        border-radius: 12px !important;
        background: #1e293b !important;
        transition: all 0.4s ease !important;
        animation: metricFloat 4s infinite ease-in-out alternate;
    }
    div[data-testid="stMetric"]:hover {
        transform: translateY(-5px) scale(1.02) !important;
        border-color: #ec4899 !important;
        box-shadow: 0 0 20px rgba(236, 72, 153, 0.3) !important;
    }
    @keyframes metricFloat {
        0% { box-shadow: 0 0 5px rgba(99, 102, 241, 0.05); }
        100% { box-shadow: 0 0 15px rgba(99, 102, 241, 0.2); }
    }

    div.stButton > button, div.stDownloadButton > button {
        background: linear-gradient(45deg, #6366f1, #ec4899) !important;
        border: none !important;
        color: white !important;
        font-weight: bold !important;
        box-shadow: 0 4px 15px rgba(99, 102, 241, 0.3) !important;
        transition: all 0.3s cubic-bezier(0.175, 0.885, 0.32, 1.275) !important;
    }
    div.stButton > button:hover, div.stDownloadButton > button:hover {
        transform: scale(1.03) translateY(-2px) !important;
        box-shadow: 0 0 25px rgba(236, 72, 153, 0.6) !important;
        filter: brightness(1.1);
    }
    div.stButton > button:active, div.stDownloadButton > button:active {
        transform: scale(0.97) !important;
    }

    input, textarea, select, div[data-baseweb="select"] {
        transition: all 0.3s ease !important;
    }
    input:focus, textarea:focus {
        border-color: #ec4899 !important;
        box-shadow: 0 0 12px rgba(236, 72, 153, 0.4) !important;
    }

    div[data-testid="stPlotlyChart"] {
        animation: chartPop 0.8s cubic-bezier(0.175, 0.885, 0.32, 1.15) forwards;
    }
    @keyframes chartPop {
        0% { transform: scale(0.95); opacity: 0; }
        100% { transform: scale(1); opacity: 1; }
    }

    .success-glitch {
        padding: 15px;
        background: linear-gradient(90deg, #10b981, #059669);
        color: white;
        border-radius: 8px;
        font-weight: bold;
        text-align: center;
        box-shadow: 0 0 20px #10b981;
        animation: alertShake 0.4s ease-in-out 2;
    }
    @keyframes alertShake {
        0%, 100% { transform: translateX(0); }
        25% { transform: translateX(-8px); }
        75% { transform: translateX(8px); }
    }
</style>
""", unsafe_allow_html=True)

THICK_LINE = "<hr style='border: 2px solid #6366f1; margin: 25px 0; opacity: 1;'>"

# ============================================================
# 3. МЕНЮ РЕЖИМОВ
# ============================================================
mode = st.sidebar.radio("Выберите режим:", ["📝 Заполнить опрос", "📊 Панель аналитики"])

COLUMN_NAMES = {
    "age": "Возраст",
    "occupation": "Род занятий",
    "sphere": "Сфера деятельности",
    "frequency": "Частота встречи с автоматизацией",
    "anxiety": "Уровень беспокойства",
    "threatened_jobs": "Профессии под угрозой",
    "impact": "Влияние на работу",
    "ready_to_retrain": "Готовность к переобучению",
    "already_learning": "Что уже изучали",
    "who_pays": "Кто должен оплачивать переобучение",
    "future_jobs": "Перспективные новые профессии",
    "ai_role": "Роль ИИ: заменит или дополнит",
    "comment": "Комментарий",
    "timestamp": "Время отправки"
}

# ============================================================
# 4. РЕЖИМ «ЗАПОЛНИТЬ ОПРОС»
# ============================================================
if mode == "📝 Заполнить опрос":
    st.markdown("<h1 class='cyber-title'>Опрос: Отношение к автоматизации труда</h1>", unsafe_allow_html=True)
    st.caption("Исследование проводится анонимно. Время заполнения: ~3 минуты.")

    with st.form("survey_form", clear_on_submit=True):
        st.subheader("Раздел 1: Профиль респондента")
        col1, col2 = st.columns(2)

        with col1:
            age = st.number_input("1. Укажите ваш возраст:", min_value=14, max_value=80, value=20, step=1)
            occupation = st.selectbox(
                "2. Ваш основной род занятий:",
                ["Школьник", "Студент", "Работаю в сфере IT", "Работаю в другой сфере", "Временно не работаю"]
            )
            sphere = st.selectbox(
                "3. Сфера деятельности:",
                ["Образование", "Информационные технологии", "Производство", "Услуги", "Медицина", "Торговля", "Другое"]
            )

        with col2:
            frequency = st.radio(
                "4. Как часто вы сталкиваетесь с автоматизацией на работе/учёбе?",
                ["Постоянно", "Несколько раз в неделю", "Редко", "Никогда"]
            )
            anxiety = st.slider("5. Уровень беспокойства, что ИИ заменит вашу профессию (1–10):", 1, 10, 5)
            impact = st.radio(
                "7. Как автоматизация влияет на вашу работу/учёбу?",
                ["Значительно повышает эффективность", "Немного повышает", "Не влияет", "Мешает"]
            )

        st.markdown(THICK_LINE, unsafe_allow_html=True)
        st.subheader("Раздел 2: Страхи и угрозы")
        threatened_jobs = st.multiselect(
            "6. Какие профессии, по вашему мнению, под угрозой автоматизации?",
            ["Кассиры и продавцы", "Водители", "Бухгалтеры", "Операторы call-центров",
             "Переводчики", "Аналитики данных", "Программисты", "Дизайнеры", "Врачи", "Учителя"]
        )

        st.markdown(THICK_LINE, unsafe_allow_html=True)
        st.subheader("Раздел 3: Переобучение и будущее")
        col3, col4 = st.columns(2)

        with col3:
            ready_to_retrain = st.radio(
                "8. Готовы ли вы переобучаться ради новой профессии?",
                ["Да, уже готовлюсь", "Да, если будет необходимость", "Нет, не планирую"]
            )
            already_learning = st.multiselect(
                "9. Что вы уже изучаете для адаптации?",
                ["Программирование", "Работу с ИИ-инструментами", "Иностранные языки",
                 "Менеджмент и коммуникации", "Ничего"]
            )
            who_pays = st.selectbox(
                "10. Кто должен оплачивать переобучение?",
                ["Государство", "Работодатель", "Сам человек", "Совместно"]
            )

        with col4:
            future_jobs = st.multiselect(
                "11. Какие новые профессии считаете перспективными?",
                ["Инженер по ИИ", "Специалист по данным", "Оператор роботов",
                 "Специалист по кибербезопасности", "Эколог-технолог", "Нейро-маркетолог"]
            )
            ai_role = st.radio(
                "12. Автоматизация заменит человека или дополнит?",
                ["Заменит полностью", "Дополнит и усилит", "Не изменит ничего"]
            )

        st.markdown(THICK_LINE, unsafe_allow_html=True)
        comment = st.text_area("13. Ваш комментарий (мнение о будущем труда):")

        submitted = st.form_submit_button("Отправить анкету в базу")

        if submitted:
            if not threatened_jobs or not future_jobs:
                st.warning("Пожалуйста, заполните обязательные множественные списки (пункты 6 и 11).")
            else:
                progress_text = "Синхронизация данных с облаком Firestore..."
                cyber_bar = st.progress(0, text=progress_text)
                for percent_complete in range(100):
                    time.sleep(0.005)
                    cyber_bar.progress(percent_complete + 1, text=progress_text)

                doc_data = {
                    "age": int(age),
                    "occupation": occupation,
                    "sphere": sphere,
                    "frequency": frequency,
                    "anxiety": int(anxiety),
                    "threatened_jobs": threatened_jobs,
                    "impact": impact,
                    "ready_to_retrain": ready_to_retrain,
                    "already_learning": already_learning,
                    "who_pays": who_pays,
                    "future_jobs": future_jobs,
                    "ai_role": ai_role,
                    "comment": comment,
                    "timestamp": datetime.utcnow()
                }

                try:
                    db.collection("responses").add(doc_data)
                    st.markdown(
                        "<div class='success-glitch'>✅ АНКЕТА УСПЕШНО ОТПРАВЛЕНА. СПАСИБО ЗА УЧАСТИЕ!</div>",
                        unsafe_allow_html=True
                    )
                    st.balloons()
                    st.toast("Данные успешно сохранены!", icon="🚀")
                except Exception as e:
                    st.error(f"Ошибка сохранения: {e}")

# ============================================================
# 5. РЕЖИМ «ПАНЕЛЬ АНАЛИТИКИ»
# ============================================================
elif mode == "📊 Панель аналитики":
    st.markdown("<h1 class='cyber-title'>Центр стратегической аналитики</h1>", unsafe_allow_html=True)

    docs = db.collection("responses").stream()
    data = [doc.to_dict() for doc in docs]

    if not data:
        st.info("В базе данных Firestore пока нет ответов.")
    else:
        df = pd.DataFrame(data)
        df["timestamp"] = pd.to_datetime(df["timestamp"]).dt.tz_localize(None)
        df_russian = df.rename(columns=COLUMN_NAMES)

        st.subheader("Ключевые показатели эффективности")
        m1, m2, m3, m4 = st.columns(4)
        with m1:
            st.metric(label="Всего респондентов", value=f"{len(df)} чел.")
        with m2:
            st.metric(label="Средний возраст", value=f"{df['age'].mean():.1f} лет")
        with m3:
            st.metric(label="Ср. уровень беспокойства", value=f"{df['anxiety'].mean():.1f} / 10")
        with m4:
            ready_count = df['ready_to_retrain'].isin(["Да, уже готовлюсь", "Да, если будет необходимость"]).sum()
            ready_percent = ready_count / len(df) * 100
            st.metric(label="Готовы переобучаться", value=f"{ready_percent:.0f}%")

        st.markdown(THICK_LINE, unsafe_allow_html=True)

        st.subheader("📥 Экспорт собранных данных")
        exp_col1, exp_col2 = st.columns(2)
        current_time = datetime.now().strftime("%Y%m%d_%H%M")

        with exp_col1:
            csv_buffer = df_russian.to_csv(index=False).encode('utf-8-sig')
            if st.download_button(
                label="🟢 Скачать базу в CSV формате",
                data=csv_buffer,
                file_name=f"survey_export_{current_time}.csv",
                mime="text/csv",
                use_container_width=True
            ):
                st.snow()
                st.toast("Файл CSV успешно сгенерирован!", icon="💾")

        with exp_col2:
            excel_buffer = io.BytesIO()
            with pd.ExcelWriter(excel_buffer, engine='openpyxl') as writer:
                df_russian.to_excel(writer, index=False, sheet_name='Ответы респондентов')
            excel_buffer.seek(0)

            if st.download_button(
                label="🔵 Скачать базу в Excel (.xlsx)",
                data=excel_buffer.getvalue(),
                file_name=f"survey_export_{current_time}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            ):
                st.snow()
                st.toast("Файл Excel успешно сгенерирован!", icon="📊")

        st.markdown(THICK_LINE, unsafe_allow_html=True)

        st.subheader("Сводная база данных (последние 10 ответов)")
        st.dataframe(df_russian.head(10), use_container_width=True)

        st.markdown(THICK_LINE, unsafe_allow_html=True)
        st.subheader("Визуальный анализ метрик")

        c1, c2 = st.columns(2)
        with c1:
            fig1 = px.histogram(
                df, x="anxiety", nbins=10,
                title="Распределение уровня беспокойства (1–10)",
                labels={"anxiety": "Уровень беспокойства"},
                color_discrete_sequence=['#38bdf8']
            )
            fig1.update_traces(marker_line_color='#0f172a', marker_line_width=2)
            fig1.update_layout(
                yaxis_title_text="Ответы",
                plot_bgcolor='#1e293b', paper_bgcolor='#1e293b', font_color='#f8fafc'
            )
            fig1.update_xaxes(showgrid=True, gridwidth=1, gridcolor='#334155', linecolor='#f8fafc', linewidth=2)
            fig1.update_yaxes(showgrid=True, gridwidth=1, gridcolor='#334155', linecolor='#f8fafc', linewidth=2)
            st.plotly_chart(fig1, use_container_width=True)

        with c2:
            fig2 = px.histogram(
                df, x="age", nbins=10,
                title="Распределение возраста респондентов",
                labels={"age": "Возраст"},
                color_discrete_sequence=['#f472b6']
            )
            fig2.update_traces(marker_line_color='#0f172a', marker_line_width=2)
            fig2.update_layout(
                yaxis_title_text="Ответы",
                plot_bgcolor='#1e293b', paper_bgcolor='#1e293b', font_color='#f8fafc'
            )
            fig2.update_xaxes(showgrid=True, gridwidth=1, gridcolor='#334155', linecolor='#f8fafc', linewidth=2)
            fig2.update_yaxes(showgrid=True, gridwidth=1, gridcolor='#334155', linecolor='#f8fafc', linewidth=2)
            st.plotly_chart(fig2, use_container_width=True)

        st.markdown(THICK_LINE, unsafe_allow_html=True)
        c3, c4 = st.columns(2)

        with c3:
            impact_counts = df['impact'].value_counts().reset_index()
            impact_counts.columns = ['impact', 'count']
            fig3 = px.bar(
                impact_counts, x='impact', y='count',
                title="Как автоматизация влияет на работу",
                labels={'impact': 'Категория', 'count': 'Количество'},
                color_discrete_sequence=['#34d399']
            )
            fig3.update_traces(marker_line_color='#0f172a', marker_line_width=2)
            fig3.update_layout(plot_bgcolor='#1e293b', paper_bgcolor='#1e293b', font_color='#f8fafc')
            fig3.update_xaxes(linecolor='#f8fafc', linewidth=2)
            fig3.update_yaxes(showgrid=True, gridwidth=1, gridcolor='#334155', linecolor='#f8fafc', linewidth=2)
            st.plotly_chart(fig3, use_container_width=True)

        with c4:
            fig4 = px.pie(
                df, names="who_pays",
                title="Кто должен оплачивать переобучение?",
                hole=0.4,
                color_discrete_sequence=['#c084fc', '#a78bfa', '#818cf8', '#6366f1']
            )
            fig4.update_traces(marker=dict(line=dict(color='#0f172a', width=2)))
            fig4.update_layout(paper_bgcolor='#1e293b', font_color='#f8fafc')
            st.plotly_chart(fig4, use_container_width=True)

        st.markdown(THICK_LINE, unsafe_allow_html=True)

        all_threatened = []
        for jobs in df['threatened_jobs']:
            if isinstance(jobs, list):
                all_threatened.extend(jobs)

        if all_threatened:
            threatened_counts = pd.Series(all_threatened).value_counts().reset_index()
            threatened_counts.columns = ['job', 'count']
            fig5 = px.bar(
                threatened_counts, x='count', y='job', orientation='h',
                title="Топ профессий под угрозой автоматизации",
                labels={'job': 'Профессия', 'count': 'Голосов'},
                color_discrete_sequence=['#fbbf24']
            )
            fig5.update_traces(marker_line_color='#0f172a', marker_line_width=2)
            fig5.update_layout(
                plot_bgcolor='#1e293b', paper_bgcolor='#1e293b', font_color='#f8fafc',
                yaxis=dict(autorange="reversed")
            )
            fig5.update_xaxes(showgrid=True, gridwidth=1, gridcolor='#334155', linecolor='#f8fafc', linewidth=2)
            st.plotly_chart(fig5, use_container_width=True)