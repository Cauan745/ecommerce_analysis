import pandas as pd
import plotly.express as px
import streamlit as st


def format_data(df_final):
    df_final["order_delivered_customer_date"] = pd.to_datetime(
        df_final["order_delivered_customer_date"], format="%Y-%m-%d %H:%M:%S"
    )

    df_final["order_estimated_delivery_date"] = pd.to_datetime(
        df_final["order_estimated_delivery_date"], format="%Y-%m-%d %H:%M:%S"
    )

    df_final["order_approved_at"] = pd.to_datetime(
        df_final["order_approved_at"], format="%Y-%m-%d %H:%M:%S"
    )

    df_final["review_creation_date"] = pd.to_datetime(
        df_final["review_creation_date"], format="%Y-%m-%d %H:%M:%S"
    )


def logistics_analysis(df_final, orders_quantity):

    df_final["delivery_time"] = (
        df_final["order_delivered_customer_date"] - df_final["order_approved_at"]
    ).dt.days

    df_final["difference_delivery_estimation"] = (
        df_final["order_estimated_delivery_date"]
        - df_final["order_delivered_customer_date"]
    ).dt.days

    average_difference_delivery_estimation = df_final[
        "difference_delivery_estimation"
    ].mean()

    delivered_late = df_final[df_final["difference_delivery_estimation"] < 0]

    late_delivery_quantity = delivered_late["order_id"].count()

    fig_prazo = px.histogram(
        df_final,
        x="difference_delivery_estimation",
        title="Distribuição: Entregas Adiantadas vs. Atrasadas",
        labels={
            "difference_delivery_estimation": "Dias (Positivo = Adiantado, Negativo = Atrasado)"
        },
    )

    fig_prazo.add_vline(
        x=0, line_dash="dash", line_color="red", annotation_text="Prazo Prometido"
    )

    late_delivery_probability = (late_delivery_quantity / orders_quantity) * 100

    on_time_quantity = orders_quantity - late_delivery_quantity

    df_status = pd.DataFrame(
        {
            "Status": ["No Prazo / Adiantado", "Atrasado"],
            "Quantidade": [on_time_quantity, late_delivery_quantity],
        }
    )

    fig_probabilidade = px.pie(
        df_status,
        names="Status",
        values="Quantidade",
        title="Probabilidade de Entrega: Atraso vs. No Prazo",
        hole=0.4,
        color="Status",
        color_discrete_map={"No Prazo / Adiantado": "#2ecc71", "Atrasado": "#e74c3c"},
    )

    delivery_histogram = px.histogram(
        df_final,
        x="delivery_time",
    )

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("Total de Pedidos", f"{orders_quantity:,}")

    with col2:
        st.metric("Probabilidade de Atraso", f"{late_delivery_probability:.2f}%")

    with col3:
        st.metric(
            "Média de Antecipação", f"{average_difference_delivery_estimation:.1f} dias"
        )

    orders_by_state = (
        df_final.groupby("customer_state")["order_id"]
        .count()
        .reset_index(name="total_orders")
    )

    late_by_state = (
        delivered_late.groupby("customer_state")["order_id"]
        .count()
        .reset_index(name="late_orders")
    )

    state_analysis = pd.merge(
        orders_by_state, late_by_state, on="customer_state", how="left"
    )

    state_analysis["late_orders"] = state_analysis["late_orders"].fillna(0)

    state_analysis["late_probability_%"] = (
        state_analysis["late_orders"] / state_analysis["total_orders"] * 100
    )

    state_analysis = state_analysis.sort_values(
        by="late_probability_%", ascending=False
    )

    fig_states = px.bar(
        state_analysis,
        x="customer_state",
        y="late_probability_%",
        title="Probabilidade Condicional de Atraso por Estado: P(Atraso | Estado)",
        labels={
            "customer_state": "Estado de Destino (UF)",
            "late_probability_%": "Probabilidade de Atraso (%)",
        },
        text_auto=".1f",
        color="late_probability_%",
        color_continuous_scale="Reds",
    )

    st.plotly_chart(delivery_histogram)
    st.plotly_chart(fig_probabilidade)
    st.plotly_chart(fig_prazo)
    st.plotly_chart(fig_states)


def satisfaction_analysis(df_final):
    reviews_distribution = px.histogram(
        df_final[
            [
                "review_id",
                "order_id",
                "review_score",
                "review_comment_title",
                "review_comment_message",
                "review_creation_date",
                "review_answer_timestamp",
            ]
        ],
        x="review_score",
    )
    reviews_distribution.update_layout(xaxis=dict(tickmode="linear", tick0=1, dtick=1))
    st.plotly_chart(reviews_distribution)

    df_final["review_delivery_date_difference"] = (
        df_final["review_creation_date"] - df_final["order_delivered_customer_date"]
    ).dt.days

    df_filtered = df_final[
        (df_final["review_delivery_date_difference"] >= 0)
        & (df_final["review_delivery_date_difference"] <= 30)
    ]

    df_trend = (
        df_filtered.groupby("review_delivery_date_difference")
        .agg(
            review_score=("review_score", "mean"),
            review_count=("review_score", "count"),
        )
        .reset_index()
    )

    df_trend_clean = df_trend[df_trend["review_count"] >= 30]

    fig = px.line(
        df_trend_clean,
        x="review_delivery_date_difference",
        y="review_score",
        title="Recency Bias: Nota Média baseada nos Dias após a Entrega (Cleaned)",
        labels={
            "review_delivery_date_difference": "Dias (Entrega -> Avaliação)",
            "review_score": "Nota Média (Estrelas)",
        },
        markers=True,
    )

    fig.add_vline(
        x=0, line_dash="dash", line_color="red", annotation_text="Dia da Entrega"
    )

    st.plotly_chart(fig)


def delivery_review_score_correlation(df_final):
    df_correlation = df_final[["delivery_time", "review_score"]]

    corr = df_correlation.corr(method="spearman").iat[0, 1]

    df_avg_delivery = df_final.groupby("review_score", as_index=False)[
        "delivery_time"
    ].mean()

    df_avg_delivery = df_avg_delivery.sort_values(by="delivery_time")

    fig = px.line(
        df_avg_delivery,
        x="delivery_time",
        y="review_score",
        title="Average Delivery Time by Review Score",
        labels={
            "review_score": "Review Score (Stars)",
            "delivery_time": "Average Delivery Time (Days)",
        },
        markers=True,
    )

    fig.update_layout(xaxis=dict(tickmode="linear", tick0=1, dtick=1))

    st.subheader("Does delivery time affect customer satisfaction?")
    st.metric(
        label="Spearman Correlation (Delivery Time vs. Review Score)",
        value=corr,
        delta="Moderate Negative Relationship",
        delta_color="inverse",
    )

    st.write(
        "Embora a correlação de Spearman (-0.23) seja considerada matematicamente 'fraca/moderada', o gráfico de linhas comprova uma realidade clara do dia a dia: quanto mais dias o pedido demora para chegar, menor tende a ser a nota de satisfação do cliente (Review Score)."
    )

    st.plotly_chart(fig)


def main():
    st.title("Análise de Logística e Satisfação: Olist E-commerce")

    st.header("1. Introdução")
    st.write("""
    **Tema e Problema:** No mercado de e-commerce, a logística é um dos maiores gargalos. 
    O problema que buscamos entender é: como o tempo de entrega e os eventuais atrasos 
    impactam diretamente a satisfação do cliente final?
    """)

    st.header("2. Objetivos do Trabalho")
    st.write("""
    * Avaliar a eficiência logística da Olist (taxa de entregas no prazo vs. atrasadas).
    * Identificar se existe uma concentração de atrasos em determinados estados.
    * Medir o impacto do tempo de entrega na nota de avaliação (Review Score) deixada pelo cliente.
    """)

    st.header("3. Metodologia Aplicada")
    st.write("""
    Foi aplicada uma **Análise Descritiva** para explorar as volumetrias e distribuições de tempo de entrega, 
    junto com a **Correlação de Spearman** para validar matematicamente a relação não-linear entre os dias 
    de entrega e a nota do cliente.
    """)

    st.markdown("---")
    st.header("4. Resultados e Apresentação dos Dados")

    df_customers = pd.read_csv("./dataset/olist_customers_dataset.csv")
    df_orders = pd.read_csv("./dataset/olist_orders_dataset.csv")
    df_orders_reviews = pd.read_csv("./dataset/olist_order_reviews_dataset.csv")

    orders_quantity = df_orders["order_id"].count()
    df_temp = pd.merge(df_customers, df_orders)
    df_final = pd.merge(df_temp, df_orders_reviews)

    format_data(df_final)

    st.subheader("Análise Logística")
    logistics_analysis(df_final, orders_quantity)

    st.subheader("Análise de Satisfação")
    satisfaction_analysis(df_final)
    delivery_review_score_correlation(df_final)

    st.markdown("---")

    st.header("5. Conclusão")
    st.write(
        "Os resultados demonstram que, embora a operação da Olist seja majoritariamente eficiente (com apenas 7.74% de probabilidade de atraso), a logística é um fator crítico para a satisfação do consumidor. Estados do Nordeste e Norte (como AL, MA e PI) sofrem com as maiores taxas de atraso. Além disso, provamos matematicamente e visualmente que o tempo de entrega dita a nota do cliente: entregas rápidas garantem avaliações de 5 estrelas, enquanto os atrasos derrubam drasticamente a reputação do vendedor."
    )


main()
