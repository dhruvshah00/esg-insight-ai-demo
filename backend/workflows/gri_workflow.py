from logging import getLogger
from llama_index.core import SimpleDirectoryReader, VectorStoreIndex, load_index_from_storage, StorageContext
from llama_index.core.node_parser import SemanticSplitterNodeParser, SentenceSplitter
from llama_index.core.response_synthesizers import CompactAndRefine
from llama_index.core.workflow import (
    Context,
    Event,
    Workflow,
    StartEvent,
    StopEvent,
    step,
)
from llama_index.core.schema import NodeWithScore
from llama_index.core.embeddings import BaseEmbedding
from llama_index.core.llms.llm import LLM
from llama_index.postprocessor.rankgpt_rerank import RankGPTRerank
from llama_index.vector_stores.faiss import FaissVectorStore
import faiss


logger = getLogger(__name__)


class RetrieverEvent(Event):
    """Result of running retrieval"""

    nodes: list[NodeWithScore]


class RerankEvent(Event):
    """Result of running reranking on retrieved nodes"""

    nodes: list[NodeWithScore]


class GRIWorkflow(Workflow):
    def __init__(self,llm: LLM,embed_model: BaseEmbedding, index: VectorStoreIndex, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.index = index
        self.llm = llm
        self.embed_model = embed_model

    @step
    async def retrieve(self, ctx: Context, ev: StartEvent) -> RetrieverEvent | None:
        "Entry point for RAG, triggered by a StartEvent with `query`."
        logger.info(f"Retrieving nodes for query: {ev.get('query')}")
        query = ev.get("query")
        top_k = ev.get("top_k", 5)
        top_n = ev.get("top_n", 3)

        if not query:
            raise ValueError("Query is required!")

        # store the settings in the global context
        await ctx.set("query", query)
        await ctx.set("top_k", top_k)
        await ctx.set("top_n", top_n)

        retriever = self.index.as_retriever(similarity_top_k=top_k)
        nodes = await retriever.aretrieve(query)
        return RetrieverEvent(nodes=nodes)

    @step
    async def rerank(self, ctx: Context, ev: RetrieverEvent) -> RerankEvent:
        # Rerank the nodes
        top_n = await ctx.get("top_n")
        query = await ctx.get("query")

        ranker = RankGPTRerank(top_n=top_n, llm=self.llm)

        try:
            new_nodes = ranker.postprocess_nodes(ev.nodes, query_str=query)
        except Exception:
            # Handle errors in the LLM response
            new_nodes = ev.nodes
        return RerankEvent(nodes=new_nodes)

    @step
    async def synthesize(self, ctx: Context, ev: RerankEvent) -> StopEvent:
        """Return a response using reranked nodes."""
        llm = self.llm
        synthesizer = CompactAndRefine(llm=llm)
        query = await ctx.get("query", default=None)

        response = await synthesizer.asynthesize(query, nodes=ev.nodes)

        return StopEvent(result=str(response))


def create_index(embed_model: BaseEmbedding) -> None:
    # create a faiss index
    d = 1024
    faiss_index = faiss.IndexFlatL2(d)
    vector_store = FaissVectorStore(faiss_index=faiss_index)
    documents = SimpleDirectoryReader("data/gri").load_data()
    
    # vector_store = FaissVectorStore(faiss_index=faiss_index)
    storage_context = StorageContext.from_defaults(vector_store=vector_store)
    
    index = VectorStoreIndex.from_documents(
        documents, storage_context=storage_context, embed_model=embed_model
    )
    index.storage_context.persist(persist_dir="./storage/gri")



def get_gri_workflow(llm: LLM,embed_model: BaseEmbedding) -> GRIWorkflow:

    vector_store = FaissVectorStore.from_persist_dir("./storage/gri")
    storage_context = StorageContext.from_defaults(
        vector_store=vector_store, persist_dir="./storage/gri"
    )
    index = load_index_from_storage(storage_context=storage_context)

    return GRIWorkflow(llm= llm,embed_model= embed_model, index=index, timeout=120.0)
