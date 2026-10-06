from datetime import datetime
import json
from bs4 import BeautifulSoup
import requests
import streamlit as st

# Configuração da Página Streamlit
st.set_page_config(
    page_title="Domus by Datum - Gerador de Orçamentos",
    page_icon="🏠",
    layout="wide",
)


def scrape_product_info(url):
  """Extrai título, preço e imagem de links de produtos utilizando

  meta tags OpenGraph, Schema.org e cabeçalhos HTTP simulando um navegador.
  """
  headers = {
      "User-Agent": (
          "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML,"
          " like Gecko) Chrome/122.0.0.0 Safari/537.36"
      ),
      "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
      "Accept": (
          "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8"
      ),
  }

  try:
    response = requests.get(url, headers=headers, timeout=10)
    if response.status_code != 200:
      return None, None, None, f"Erro HTTP: {response.status_code}"

    soup = BeautifulSoup(response.text, "html.parser")

    # 1. Extração de Título
    title = None
    og_title = soup.find("meta", property="og:title")
    if og_title and og_title.get("content"):
      title = og_title.get("content").strip()
    elif soup.title:
      title = soup.title.string.strip()

    # 2. Extração de Imagem
    image_url = None
    og_image = soup.find("meta", property="og:image")
    if og_image and og_image.get("content"):
      image_url = og_image.get("content").strip()

    # 3. Extração de Preço
    price = 0.0
    og_price = soup.find("meta", property="product:price:amount")
    if og_price and og_price.get("content"):
      try:
        price = float(
            og_price.get("content")
            .replace("R$", "")
            .replace(".", "")
            .replace(",", ".")
            .strip()
        )
      except ValueError:
        pass

    # Fallback para JSON-LD (Schema.org)
    if price == 0.0:
      for script in soup.find_all("script", type="application/ld+json"):
        try:
          data = json.loads(script.string)
          if isinstance(data, list):
            data = data[0]
          if data.get("@type") == "Product" and "offers" in data:
            offers = data["offers"]
            if isinstance(offers, list):
              offers = offers[0]
            price = float(str(offers.get("price", 0.0)).replace(",", "."))
            break
        except Exception:
          continue

    return title, price, image_url, None

  except Exception as e:
    return None, None, None, str(e)


# Inicialização do Estado da Sessão
if "itens" not in st.session_state:
  st.session_state.itens = []
if "numero_orcamento" not in st.session_state:
  st.session_state.numero_orcamento = "DOM-1006"

# Cabeçalho da Aplicação
st.title("Domus by Datum")
st.markdown("*Precision in every room* — Gerador de Orçamentos")
st.divider()

# Seção 1: Dados Gerais do Cliente
st.subheader("1. Dados do Cliente e Orçamento")
col1, col2, col3 = st.columns(3)
with col1:
  num_orc = st.text_input(
      "Número do Orçamento", value=st.session_state.numero_orcamento
  )
with col2:
  cliente_nome = st.text_input("Nome do Cliente / Projeto")
with col3:
  data_orc = st.date_input("Data de Emissão", value=datetime.now())

st.divider()

# Seção 2: Adicionar Produtos (com Raspagem ou Fallback Manual)
st.subheader("2. Adicionar Equipamentos / Produtos")
url_input = st.text_input("Link do Produto (Opcional - Mercado Livre, Lojas, etc.)")

scraped_title, scraped_price, scraped_img = "", 0.0, ""

if url_input:
  if st.button("Buscar Dados do Link"):
    with st.spinner("Buscando informações do produto..."):
      t, p, i, err = scrape_product_info(url_input)
      if err:
        st.warning(
            f"Não foi possível importar automaticamente ({err}). Preencha os"
            " campos abaixo manualmente:"
        )
      else:
        st.success("Dados importados com sucesso!")
        scraped_title, scraped_price, scraped_img = t or "", p or 0.0, i or ""

with st.form("form_produto", clear_on_submit=True):
  desc = st.text_input("Descrição do Item", value=scraped_title)
  col_a, col_b = st.columns(2)
  with col_a:
    qtd = st.number_input("Quantidade", min_value=1, value=1)
  with col_b:
    preco_unit = st.number_input(
        "Preço Unitário (R$)",
        value=float(scraped_price) if scraped_price else 0.0,
        format="%.2f",
    )

  img_url = st.text_input("URL da Imagem", value=scraped_img)

  submitted = st.form_submit_button("Adicionar à Lista de Itens")
  if submitted:
    if desc.strip() == "":
      st.error("A descrição do produto não pode estar vazia.")
    else:
      st.session_state.itens.append({
          "descricao": desc,
          "quantidade": qtd,
          "preco_unitario": preco_unit,
          "total": qtd * preco_unit,
          "imagem": img_url,
      })
      st.success(f"Item '{desc}' adicionado com sucesso!")
      st.rerun()

# Listagem dos Itens Adicionados
if st.session_state.itens:
  st.divider()
  st.subheader("3. Itens Selecionados")

  subtotal_produtos = 0.0
  for i, item in enumerate(st.session_state.itens):
    subtotal_produtos += item["total"]
    col_item1, col_item2, col_item3, col_item4, col_item5 = st.columns(
        [3, 1, 1, 1, 1]
    )
    col_item1.write(f"**{item['descricao']}**")
    col_item2.write(f"Qtd: {item['quantidade']}")
    col_item3.write(f"R$ {item['preco_unitario']:.2f}")
    col_item4.write(f"R$ {item['total']:.2f}")
    if col_item5.button("Remover", key=f"del_{i}"):
      st.session_state.itens.pop(i)
      st.rerun()

  st.markdown(f"### Subtotal dos Produtos: R$ {subtotal_produtos:.2f}")

  # Seção 4: Mão de Obra e Totais
  st.divider()
  st.subheader("4. Mão de Obra e Condições de Pagamento")

  percentual_mao_obra = st.slider(
      "Percentual de Mão de Obra (%)", 0.0, 100.0, 35.0
  )
  valor_mao_obra = subtotal_produtos * (percentual_mao_obra / 100.0)
  valor_total = subtotal_produtos + valor_mao_obra

  st.info(
      f"**Cálculo:** Mão de obra ({percentual_mao_obra}%): **R$"
      f" {valor_mao_obra:.2f}** | **Valor Total Geral:** **R$"
      f" {valor_total:.2f}**"
  )

  # Geração do Arquivo HTML A4
  if st.button("Gerar Documento HTML para Impressão"):
    html_content = f"""
        <!DOCTYPE html>
        <html lang="pt-BR">
        <head>
            <meta charset="UTF-8">
            <title>Orçamento {num_orc} - Domus by Datum</title>
            <style>
                body {{ font-family: 'Helvetica Neue', Arial, sans-serif; margin: 40px; color: #333; line-height: 1.6; }}
                .header {{ text-align: center; border-bottom: 2px solid #222; padding-bottom: 15px; margin-bottom: 30px; }}
                .header h1 {{ margin: 0; font-size: 28px; color: #111; }}
                .tagline {{ font-style: italic; color: #555; font-size: 14px; margin-top: 5px; }}
                .info-box {{ margin-bottom: 20px; font-size: 14px; }}
                table {{ width: 100%; border-collapse: collapse; margin-top: 20px; margin-bottom: 20px; }}
                th, td {{ border: 1px solid #ddd; padding: 12px; text-align: left; font-size: 14px; }}
                th {{ background-color: #f8f9fa; color: #222; }}
                .totals {{ text-align: right; margin-top: 20px; font-size: 15px; }}
                .totals h3 {{ color: #000; font-size: 20px; }}
                .payment-box {{ margin-top: 30px; padding: 15px; background: #f9f9f9; border-left: 4px solid #333; font-size: 13px; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>Domus by Datum</h1>
                <div class="tagline">Precision in every room</div>
                <h2>Orçamento Técnico: {num_orc}</h2>
            </div>
            
            <div class="info-box">
                <p><strong>Cliente:</strong> {cliente_nome if cliente_nome else "Cliente"}</p>
                <p><strong>Data de Emissão:</strong> {data_orc.strftime('%d/%m/%Y')}</p>
            </div>

            <table>
                <thead>
                    <tr>
                        <th>Descrição do Item</th>
                        <th>Qtd</th>
                        <th>Preço Unit.</th>
                        <th>Total</th>
                    </tr>
                </thead>
                <tbody>
        """

    for item in st.session_state.itens:
      html_content += f"""
                    <tr>
                        <td>{item['descricao']}</td>
                        <td>{item['quantidade']}</td>
                        <td>R$ {item['preco_unitario']:,.2f}</td>
                        <td>R$ {item['total']:,.2f}</td>
                    </tr>
        """

    html_content += f"""
                </tbody>
            </table>

            <div class="totals">
                <p>Subtotal Equipamentos: R$ {subtotal_produtos:,.2f}</p>
                <p>Mão de Obra ({percentual_mao_obra}%): R$ {valor_mao_obra:,.2f}</p>
                <h3>Valor Total do Projeto: R$ {valor_total:,.2f}</h3>
            </div>

            <div class="payment-box">
                <strong>Condições de Pagamento:</strong><br>
                50% de entrada no aceite da proposta e 50% na conclusão da entrega técnica.<br>
                Validade da proposta: 10 dias.
            </div>
        </body>
        </html>
        """

    st.download_button(
        label="📥 Baixar Orçamento HTML (Pronto para Impressão A4)",
        data=html_content,
        file_name=f"orcamento_{num_orc.lower()}.html",
        mime="text/html",
    )
else:
  st.info(
      "Nenhum item adicionado ao orçamento. Insira um link acima ou preencha"
      " manualmente."
  )