import { useEffect, useRef, useState } from 'react'
import HomePage from './pages/HomePage'
import DebatePage from './pages/DebatePage'
import ResultPage from './pages/ResultPage'
import { buscarPersonas, conectarFeed, criarSimulacao } from './services/api'
import type { MensagemDebate, NegocioPayload, PersonaPublica, PesquisaMercado, ResultadoSimulacao } from './types'
import LandingPage from './pages/LandingPage'

type Tela = 'apresentacao' | 'inicio' | 'debate' | 'resultado'

export default function App() {
  const [tela, setTela] = useState<Tela>('apresentacao')
  const [personas, setPersonas] = useState<PersonaPublica[]>([])
  const [mensagens, setMensagens] = useState<MensagemDebate[]>([])
  const [resultado, setResultado] = useState<ResultadoSimulacao | null>(null)
  const [pesquisa, setPesquisa] = useState<PesquisaMercado | null>(null)
  const [carregando, setCarregando] = useState(false)
  const [erroFormulario, setErroFormulario] = useState('')
  const [erroFeed, setErroFeed] = useState('')
  const [statusTexto, setStatusTexto] = useState('Preparando os agentes para a avaliação...')
  const [rodadaAtual, setRodadaAtual] = useState<1 | 2>(1)
  const fonteRef = useRef<EventSource | null>(null)

  function abrirFormulario() {
  window.history.pushState({ tela: 'inicio' }, '')
  setTela('inicio')
  }

  useEffect(() => {
    buscarPersonas()
      .then(setPersonas)
      .catch(() => {
        setErroFormulario('Não foi possível conectar à API do MarketMind. Confira se o backend está rodando em http://localhost:8000.')
      })

    return () => fonteRef.current?.close()
  }, [])


  useEffect(() => {
  function voltarPagina(evento: PopStateEvent) {
    if (evento.state?.tela === 'inicio') {
      setTela('inicio')
    } else {
      setTela('apresentacao')
    }
  }

  window.addEventListener('popstate', voltarPagina)

  return () => {
    window.removeEventListener('popstate', voltarPagina)
  }
  }, [])

  // Só as personas que participam desta simulação (o usuário escolhe quantas)
  const [participantes, setParticipantes] = useState<string[]>([])
  const personasDaSimulacao = participantes.length
    ? personas.filter((p) => participantes.includes(p.id))
    : personas

  async function avaliar(negocio: NegocioPayload, demo: boolean, escolhidas: string[]) {
    setCarregando(true)
    setErroFormulario('')
    setErroFeed('')
    setMensagens([])
    setResultado(null)
    setPesquisa(null)
    setRodadaAtual(1)
    setStatusTexto(`Iniciando os ${escolhidas.length} agentes...`)
    fonteRef.current?.close()
    fonteRef.current = null

    try {
      const simulacao = await criarSimulacao(negocio, demo, escolhidas)
      setParticipantes(simulacao.personas ?? escolhidas)
      setTela('debate')
      setStatusTexto('Os agentes estão lendo as informações do produto...')

      fonteRef.current = conectarFeed(simulacao.id, {
        aoReceberMensagem: (mensagem) => {
          setMensagens((atuais) => [...atuais, mensagem])
          if (mensagem.rodada === 2) {
            setRodadaAtual(2)
            setStatusTexto('Os agentes estão reagindo às opiniões uns dos outros...')
          } else {
            setStatusTexto('As primeiras avaliações estão chegando...')
          }
        },
        aoIniciarPesquisa: () => {
          setStatusTexto('O pesquisador está buscando preços e lojas parecidas na região...')
        },
        aoReceberPesquisa: (pesquisaRecebida) => {
          setPesquisa(pesquisaRecebida)
          setStatusTexto('Pesquisa de mercado concluída. Os agentes estão lendo as informações do produto...')
        },
        aoIniciarAnalise: () => {
          setRodadaAtual(2)
          setStatusTexto('Debate concluído. O analista está lendo tudo e escrevendo o relatório...')
        },
        aoFinalizar: (resultadoFinal) => {
          setMensagens(resultadoFinal.mensagens)
          setResultado(resultadoFinal)
          setRodadaAtual(2)
          setStatusTexto('Debate concluído. Preparando o panorama da avaliação...')
          setTela('resultado')
        },
        aoFalhar: (mensagem) => {
          setErroFeed(mensagem)
          setStatusTexto('A avaliação foi interrompida.')
        },
        aoReconectar: () => {
          setStatusTexto('Conexão instável. Tentando reconectar ao feed...')
        },
      })
    } catch (erro) {
      setErroFormulario(erro instanceof Error ? erro.message : 'Ocorreu um erro ao iniciar a avaliação.')
      setTela('inicio')
    } finally {
      setCarregando(false)
    }
  }

  function novaAvaliacao() {
    fonteRef.current?.close()
    fonteRef.current = null
    setTela('inicio')
    setMensagens([])
    setResultado(null)
    setPesquisa(null)
    setErroFeed('')
    setErroFormulario('')
    setRodadaAtual(1)
    setStatusTexto('Preparando os agentes para a avaliação...')
  }

  if (tela === 'apresentacao') {
  return (
    <LandingPage
      onComecar={abrirFormulario}
    />
  )
  }

  if (tela === 'resultado' && resultado) {
    return <ResultPage personas={personasDaSimulacao} resultado={resultado} onNovaAvaliacao={novaAvaliacao} />
  }

  if (tela === 'debate') {
    return (
      <DebatePage
        personas={personasDaSimulacao}
        mensagens={mensagens}
        rodadaAtual={rodadaAtual}
        pesquisa={pesquisa}
        statusTexto={statusTexto}
        erro={erroFeed}
        onVoltar={novaAvaliacao}
      />
    )
  }

  return <HomePage personas={personas} carregando={carregando} erro={erroFormulario} aoAvaliar={avaliar} />
}
