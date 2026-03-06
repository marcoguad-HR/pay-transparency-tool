"""Unit test per il supporto Markdown/TXT nell'ingestion pipeline."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.rag.ingestion import DirectiveIngestion


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_chunk(text: str, source: str) -> MagicMock:
    """Crea un Chunk-like mock con text e metadata."""
    chunk = MagicMock()
    chunk.text = text
    chunk.metadata = {"source": source}
    chunk.id = "test-id"
    return chunk


# ---------------------------------------------------------------------------
# Fixture
# ---------------------------------------------------------------------------

@pytest.fixture
def ingestion(tmp_path):
    """DirectiveIngestion con tutte le dipendenze pesanti mockate."""
    with patch("src.rag.ingestion.TextEmbedding"), \
         patch("src.rag.ingestion.QdrantVectorstore"), \
         patch("src.rag.ingestion.TextParser"), \
         patch("src.rag.ingestion.RecursiveSplitter"), \
         patch("src.rag.ingestion.Config") as mock_cfg:

        cfg = mock_cfg.get_instance.return_value
        cfg.embeddings_config = {"model_name": "test-model", "dimensions": 384}
        cfg.vectorstore_config = {
            "location": str(tmp_path / "vectordb"),
            "collection_name": "test_collection",
        }
        cfg.rag_config = {"chunk_size": 1000, "chunk_overlap": 200}

        yield DirectiveIngestion()


# ---------------------------------------------------------------------------
# _extract_text_from_markdown
# ---------------------------------------------------------------------------

class TestExtractTextFromMarkdown:

    def test_legge_file_md(self, ingestion, tmp_path):
        """Legge il contenuto di un file .md correttamente."""
        md_file = tmp_path / "test.md"
        md_file.write_text("# Titolo\n\nContenuto del documento.", encoding="utf-8")

        text = ingestion._extract_text_from_markdown(str(md_file))

        assert "# Titolo" in text
        assert "Contenuto del documento." in text

    def test_legge_file_txt(self, ingestion, tmp_path):
        """Legge il contenuto di un file .txt correttamente."""
        txt_file = tmp_path / "note.txt"
        txt_file.write_text("Paragrafo uno.\n\nParagrafo due.", encoding="utf-8")

        text = ingestion._extract_text_from_markdown(str(txt_file))

        assert "Paragrafo uno." in text
        assert "Paragrafo due." in text

    def test_gestisce_caratteri_utf8(self, ingestion, tmp_path):
        """Gestisce caratteri speciali UTF-8 (accenti, €, —)."""
        md_file = tmp_path / "euro.md"
        md_file.write_text("Gap salariale: €50.000 — analisi détaillée.", encoding="utf-8")

        text = ingestion._extract_text_from_markdown(str(md_file))

        assert "€50.000" in text
        assert "détaillée" in text

    def test_compatta_righe_vuote_eccessive(self, ingestion, tmp_path):
        """Più di 2 righe vuote consecutive vengono ridotte a 2 (= 3 newline)."""
        content = "Primo\n\n\n\n\nSecondo"  # 4 righe vuote
        md_file = tmp_path / "spaced.md"
        md_file.write_text(content, encoding="utf-8")

        text = ingestion._extract_text_from_markdown(str(md_file))

        # 2 righe vuote = "\n\n\n" — al massimo 3 newline consecutive
        assert "\n\n\n\n" not in text
        assert "Primo" in text
        assert "Secondo" in text

    def test_file_vuoto(self, ingestion, tmp_path):
        """Un file vuoto restituisce stringa vuota senza errori."""
        empty = tmp_path / "empty.md"
        empty.write_text("", encoding="utf-8")

        text = ingestion._extract_text_from_markdown(str(empty))

        assert text == ""


# ---------------------------------------------------------------------------
# _add_chunk_headers — Markdown
# ---------------------------------------------------------------------------

class TestAddChunkHeadersMarkdown:

    def test_riconosce_h1(self, ingestion):
        """Un heading # genera un header 'Sezione: ...'."""
        chunk = _make_chunk(
            "# Obblighi di trasparenza\n\nLe aziende devono...",
            source="/docs/guida.md",
        )
        result = ingestion._add_chunk_headers([chunk])

        assert "[Sezione: Obblighi di trasparenza]" in result[0].text
        assert result[0].metadata["article_header"] == "Sezione: Obblighi di trasparenza"

    def test_riconosce_h2(self, ingestion):
        """Un heading ## genera un header 'Sottosezione: ...'."""
        chunk = _make_chunk(
            "## Aziende con 50-249 dipendenti\n\nObblighi specifici...",
            source="/docs/guida.md",
        )
        result = ingestion._add_chunk_headers([chunk])

        assert "[Sottosezione: Aziende con 50-249 dipendenti]" in result[0].text
        assert result[0].metadata["article_header"] == "Sottosezione: Aziende con 50-249 dipendenti"

    def test_header_si_propaga_ai_chunk_successivi(self, ingestion):
        """L'ultimo heading trovato si propaga ai chunk che non ne hanno uno."""
        chunks = [
            _make_chunk("# Sezione Uno\nContenuto iniziale.", "/docs/d.md"),
            _make_chunk("Continuazione senza heading.", "/docs/d.md"),
        ]
        result = ingestion._add_chunk_headers(chunks)

        assert "[Sezione: Sezione Uno]" in result[0].text
        assert "[Sezione: Sezione Uno]" in result[1].text

    def test_chunk_senza_heading_non_ha_header(self, ingestion):
        """Se il documento non ha heading, nessun header viene preposto."""
        chunk = _make_chunk("Testo senza heading.", source="/docs/note.md")
        result = ingestion._add_chunk_headers([chunk])

        assert result[0].text == "Testo senza heading."
        assert "article_header" not in result[0].metadata

    def test_txt_usa_stessa_logica_di_md(self, ingestion):
        """I file .txt usano lo stesso parser Markdown (# heading)."""
        chunk = _make_chunk("# Nota\nContenuto.", source="/docs/note.txt")
        result = ingestion._add_chunk_headers([chunk])

        assert "[Sezione: Nota]" in result[0].text

    def test_lista_vuota(self, ingestion):
        """Lista vuota restituisce lista vuota senza errori."""
        result = ingestion._add_chunk_headers([])
        assert result == []


# ---------------------------------------------------------------------------
# _add_chunk_headers — PDF (backward compat)
# ---------------------------------------------------------------------------

class TestAddChunkHeadersPDF:

    def test_riconosce_article_pattern(self, ingestion):
        """Il pattern 'Article N\\nTitolo' dei PDF continua a funzionare."""
        chunk = _make_chunk(
            "Article 9\nPay reporting\nMember States shall...",
            source="/docs/directive.pdf",
        )
        result = ingestion._add_pdf_article_headers([chunk])

        assert "[Article 9 - Pay reporting]" in result[0].text
        assert result[0].metadata["article_header"] == "Article 9 - Pay reporting"

    def test_dispatch_a_pdf_per_file_pdf(self, ingestion):
        """_add_chunk_headers delega a _add_pdf_article_headers per .pdf."""
        chunk = _make_chunk("Article 1\nPurpose\nThis directive...", "/docs/dir.pdf")

        with patch.object(ingestion, "_add_pdf_article_headers",
                          wraps=ingestion._add_pdf_article_headers) as spy:
            ingestion._add_chunk_headers([chunk])

        spy.assert_called_once()

    def test_dispatch_a_markdown_per_file_md(self, ingestion):
        """_add_chunk_headers delega a _add_markdown_headers per .md."""
        chunk = _make_chunk("# Heading\nContent", "/docs/guide.md")

        with patch.object(ingestion, "_add_markdown_headers",
                          wraps=ingestion._add_markdown_headers) as spy:
            ingestion._add_chunk_headers([chunk])

        spy.assert_called_once()


# ---------------------------------------------------------------------------
# ingest() — routing file vs cartella
# ---------------------------------------------------------------------------

class TestIngestRouting:

    def test_ingest_file_md_chiama_single_file(self, ingestion, tmp_path):
        """ingest() su file .md delega a _ingest_single_file."""
        md = tmp_path / "doc.md"
        md.write_text("# Test\nContenuto.", encoding="utf-8")

        with patch.object(ingestion, "_ingest_single_file", return_value=5) as mock_single:
            result = ingestion.ingest(str(md))

        mock_single.assert_called_once_with(str(md))
        assert result == 5

    def test_ingest_directory_chiama_ingest_directory(self, ingestion, tmp_path):
        """ingest() su cartella delega a _ingest_directory."""
        with patch.object(ingestion, "_ingest_directory", return_value=10) as mock_dir:
            result = ingestion.ingest(str(tmp_path))

        mock_dir.assert_called_once_with(tmp_path)
        assert result == 10

    def test_ingest_unsupported_extension_raises(self, ingestion, tmp_path):
        """Un file con estensione non supportata solleva ValueError."""
        bad_file = tmp_path / "data.json"
        bad_file.write_text("{}", encoding="utf-8")

        with pytest.raises(ValueError, match="non supportato"):
            ingestion.ingest(str(bad_file))


# ---------------------------------------------------------------------------
# _ingest_directory
# ---------------------------------------------------------------------------

class TestIngestDirectory:

    def _setup_dir(self, tmp_path):
        (tmp_path / "doc.pdf").write_bytes(b"%PDF-")
        (tmp_path / "guida.md").write_text("# Guida\nContenuto.", encoding="utf-8")
        (tmp_path / "note.txt").write_text("Note varie.", encoding="utf-8")
        return tmp_path

    def test_cartella_vuota_ritorna_zero(self, ingestion, tmp_path):
        """Una cartella senza file supportati ritorna 0 chunk."""
        (tmp_path / "data.json").write_text("{}")
        result = ingestion._ingest_directory(tmp_path)
        assert result == 0

    def test_cartella_mista_processa_tutti_i_tipi(self, ingestion, tmp_path):
        """I file .pdf, .md e .txt vengono tutti processati."""
        self._setup_dir(tmp_path)
        fake_chunks = [_make_chunk("testo", "/f.md")]

        with patch.object(ingestion, "_extract_embed_store", return_value=fake_chunks) as mock_ees, \
             patch.object(ingestion, "_build_bm25_index"):
            result = ingestion._ingest_directory(tmp_path)

        assert mock_ees.call_count == 3  # 1 pdf + 1 md + 1 txt
        assert result == 3              # 3 file × 1 chunk ciascuno

    def test_bm25_ricostruito_con_tutti_i_chunk(self, ingestion, tmp_path):
        """L'indice BM25 viene ricostruito con i chunk di TUTTI i file."""
        (tmp_path / "a.md").write_text("# A\nContenuto A.", encoding="utf-8")
        (tmp_path / "b.md").write_text("# B\nContenuto B.", encoding="utf-8")

        chunks_a = [_make_chunk("Contenuto A", "/a.md")]
        chunks_b = [_make_chunk("Contenuto B", "/b.md")]

        def fake_ees(fp):
            return chunks_a if "a.md" in fp else chunks_b

        with patch.object(ingestion, "_extract_embed_store", side_effect=fake_ees), \
             patch.object(ingestion, "_build_bm25_index") as mock_bm25:
            ingestion._ingest_directory(tmp_path)

        mock_bm25.assert_called_once()
        called_chunks = mock_bm25.call_args[0][0]
        assert len(called_chunks) == 2

    def test_bm25_non_chiamato_se_nessun_chunk(self, ingestion, tmp_path):
        """Se _extract_embed_store ritorna vuoto, BM25 non viene chiamato."""
        (tmp_path / "empty.md").write_text("", encoding="utf-8")

        with patch.object(ingestion, "_extract_embed_store", return_value=[]), \
             patch.object(ingestion, "_build_bm25_index") as mock_bm25:
            ingestion._ingest_directory(tmp_path)

        mock_bm25.assert_not_called()


# ---------------------------------------------------------------------------
# _extract_embed_store — dispatch estrazione
# ---------------------------------------------------------------------------

class TestExtractEmbedStore:

    def test_usa_extract_markdown_per_md(self, ingestion, tmp_path):
        """_extract_embed_store chiama _extract_text_from_markdown per .md."""
        md = tmp_path / "doc.md"
        md.write_text("# Test\nContenuto.")

        with patch.object(ingestion, "_extract_text_from_markdown", return_value="testo") as mock_md, \
             patch.object(ingestion, "_parse_text", return_value=MagicMock()), \
             patch.object(ingestion, "_split_into_chunks", return_value=[]), \
             patch.object(ingestion, "_add_chunk_headers", return_value=[]), \
             patch.object(ingestion, "_embed_chunks", return_value=[]), \
             patch.object(ingestion, "_store_chunks"):
            ingestion._extract_embed_store(str(md))

        mock_md.assert_called_once_with(str(md))

    def test_usa_extract_text_per_pdf(self, ingestion, tmp_path):
        """_extract_embed_store chiama _extract_text per .pdf."""
        pdf = tmp_path / "dir.pdf"
        pdf.write_bytes(b"%PDF-")

        with patch.object(ingestion, "_extract_text", return_value="testo") as mock_pdf, \
             patch.object(ingestion, "_parse_text", return_value=MagicMock()), \
             patch.object(ingestion, "_split_into_chunks", return_value=[]), \
             patch.object(ingestion, "_add_chunk_headers", return_value=[]), \
             patch.object(ingestion, "_embed_chunks", return_value=[]), \
             patch.object(ingestion, "_store_chunks"):
            ingestion._extract_embed_store(str(pdf))

        mock_pdf.assert_called_once_with(str(pdf))

    def test_usa_extract_markdown_per_txt(self, ingestion, tmp_path):
        """_extract_embed_store chiama _extract_text_from_markdown per .txt."""
        txt = tmp_path / "note.txt"
        txt.write_text("Note varie.")

        with patch.object(ingestion, "_extract_text_from_markdown", return_value="testo") as mock_md, \
             patch.object(ingestion, "_parse_text", return_value=MagicMock()), \
             patch.object(ingestion, "_split_into_chunks", return_value=[]), \
             patch.object(ingestion, "_add_chunk_headers", return_value=[]), \
             patch.object(ingestion, "_embed_chunks", return_value=[]), \
             patch.object(ingestion, "_store_chunks"):
            ingestion._extract_embed_store(str(txt))

        mock_md.assert_called_once_with(str(txt))
