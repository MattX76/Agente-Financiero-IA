# graph.py
import os
import psycopg
from psycopg.rows import dict_row
from typing import TypedDict, Annotated, List
from langchain_core.messages import BaseMessage, AIMessage, HumanMessage, SystemMessage
from langgraph.graph import StateGraph, END

# Importa el saver de Postgres
from langgraph.checkpoint.postgres import PostgresSaver

from agents import initialize_agents, get_supervisor_prompt, get_shared_llm

class AgentState(TypedDict):
    messages: Annotated[List[BaseMessage], list.__add__]
    next: str

def create_financial_assistant_graph():
    # 1) Inicializar LLM y agentes
    llm = get_shared_llm()
    agents = initialize_agents()
    sup_prompt = get_supervisor_prompt()

    # 2) Construir el grafo
    graph = StateGraph[AgentState]()

    @graph.on_start()
    def start() -> AgentState:
        sys_msg = SystemMessage(content=sup_prompt.messages[0].prompt.template)
        return AgentState(messages=[sys_msg], next="SUPERVISOR")

    @graph.node("SUPERVISOR")
    def supervisor(state: AgentState) -> AgentState:
        sys_msg = state["messages"][0]
        history = "\n".join(f"{type(m).__name__}: {m.content}" for m in state["messages"])
        human_tmpl = sup_prompt.messages[1].prompt
        human_msg = HumanMessage(content=human_tmpl.format(messages=history))

        res = llm.generate(messages=[sys_msg, human_msg])
        ai_msg = res.generations[0][0].message
        state["messages"].append(ai_msg)
        state["next"] = ai_msg.content.strip()
        return state

    # 3) Nodos para cada agente especializado
    for name, executor in agents.items():
        def _make_node(n: str, execu):
            @graph.node(n)
            def _agent(state: AgentState) -> AgentState:
                reply = execu.run(messages=state["messages"])
                state["messages"].append(AIMessage(content=reply))
                state["next"] = "SUPERVISOR"
                return state
        _make_node(name, executor)

    @graph.node("FINAL_ANSWER")
    def final_answer(state: AgentState) -> END:
        last_ai = next((m for m in reversed(state["messages"]) if isinstance(m, AIMessage)), None)
        return END(last_ai or "⚠️ Sin respuesta.")

    # 4) Configurar PostgresSaver como checkpointer
    DB_URI = os.environ.get(
        "GRAPH_CHECKPOINT_DB_URI",
        "postgresql://primera-base:primera-base@34.130.1.177:5432/postgres?sslmode=disable"
    )
    # Conectar con autocommit y row_factory=dict_row
    conn = psycopg.connect(DB_URI, autocommit=True, row_factory=dict_row)
    saver = PostgresSaver(conn)
    saver.setup()  # crea las tablas si aún no existen :contentReference[oaicite:1]{index=1}

    # 5) Compilar el grafo con el saver de Postgres
    return graph.compile(checkpointer=saver)

if __name__ == "__main__":
    app = create_financial_assistant_graph()
    print("✅ Grafo compilado con PostgresSaver:", app)
