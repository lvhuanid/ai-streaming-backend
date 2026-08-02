from typing import List
from langchain_text_splitters import MarkdownHeaderTextSplitter, RecursiveCharacterTextSplitter
from src.models import DocumentChunk, ChunkMetadata

class CascadeDocumentChunker:
    """Markdown 级联切片器：基于 Markdown 结构层级优先切分，超长块按字符/标点级联递归切分"""

    def __init__(self, chunk_size: int = 500, chunk_overlap: int = 50):
        self.headers_to_split_on = [
            ("#", "Header 1"),
            ("##", "Header 2"),
            ("###", "Header 3"),
        ]
        self.md_splitter = MarkdownHeaderTextSplitter(
            headers_to_split_on=self.headers_to_split_on,
            strip_headers=False
        )
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separators=["\n```\n", "\n\n", "\n", "。", "！", "？", " ", ""]
        )

    def chunk(self, doc_id: str, content: str) -> List[DocumentChunk]:
        # Step 1: Markdown 结构层级初切
        md_docs = self.md_splitter.split_text(content)
        final_chunks: List[DocumentChunk] = []
        chunk_counter = 0

        for doc in md_docs:
            header_context = " > ".join([str(v) for v in doc.metadata.values()]) if doc.metadata else "Root"
            
            # Step 2: 超长内容递归级联二次切分
            sub_texts = self.text_splitter.split_text(doc.page_content)
            
            for sub_text in sub_texts:
                chunk_id = f"{doc_id}_{chunk_counter}"
                metadata = ChunkMetadata(
                    doc_id=doc_id,
                    chunk_id=chunk_id,
                    section_heading=header_context,
                    start_char_idx=0,
                    end_char_idx=len(sub_text)
                )
                final_chunks.append(DocumentChunk(
                    chunk_id=chunk_id,
                    content=sub_text,
                    metadata=metadata
                ))
                chunk_counter += 1
                
        return final_chunks
