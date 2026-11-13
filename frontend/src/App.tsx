import { useEffect, useRef, useState } from 'react'
import HomePage from './pages/HomePage'
import DebatePage from './pages/DebatePage'
import ResultPage from './pages/ResultPage'
import { buscarEspecialistas, buscarPersonas, conectarFeed, criarSimulacao } from './services/api'
import type {
  EspecialistaPublico,
  MensagemDebate,
  MensagemParecer,
  NegocioPayload,
  PersonaPublica,
  PesquisaMercado,
  ResultadoSimulacao,
} from './types'
import LandingPage from './pages/LandingPage'

type Tela = 'apresentacao' | 'inicio' | 'debate' | 'resultado'

export default function App() {
  const [tela, setTela] = useState<Tela>('apresentacao')
  const [personas, setPersonas] = useState<PersonaPublica[]>([])
  const [especialistas, setEspecialistas] = useState<EspecialistaPublico[]>([])
  const [mensagens, setMensagens] = useState<MensagemDebate[]>([])
  const [pareceres, setPareceres] = useState<MensagemParecer[]>([])
  const [resultado, setResultado] = useState<ResultadoSimulacao | null>(null)
  const [pesquisa, setPesquisa] = useState<PesquisaMercado | null>(null)
  const [carregando, setCarregando] = useState(false)
  const [erroFormulario, setErroFormulario] = useState('')
  const [erroFeed, setErroFeed] = useState('')
  const [statusTexto, setStatusTexto] = useState('Preparando os agentes para a avaliação...')
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
    buscarEspecialistas()
      .then(setEspecialistas)
      .catch(() => setEspecialistas([])) // backend antigo, sem especialistas: o resto continua funcionando

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

  // Só os agentes que participam desta simulação (o usuário escolhe quais)
  const [participantes, setParticipantes] = useState<string[] | null>(null)
  const personasDaSimulacao = participantes ? personas.filter((p) => participantes.includes(p.id)) : personas
  const especialistasDaSimulacao = participantes ? especialistas.filter((e) => participantes.includes(e.id)) : especialistas

  async function avaliar(negocio: NegocioPayload, demo: boolean, escolhidas: string[]) {
    setCarregando(true)
    setErroFormulario('')
    setErroFeed('')
    setMensagens([])
    setPareceres([])
    setResultado(null)
    setPesquisa(null)
    setStatusTexto(`Iniciando os ${escolhidas.length} agentes...`)
    fonteRef.current?.close()
    fonteRef.current = null

    try {
      const simulacao = await criarSimulacao(negocio, demo, escolhidas)
      setParticipantes([...(simulacao.personas ?? []), ...(simulacao.especialistas ?? [])].length
        ? [...(simulacao.personas ?? []), ...(simulacao.especialistas ?? [])]
        : escolhidas)
      setTela('debate')
      setStatusTexto('Os agentes estão lendo as informações do produto...')

      fonteRef.current = conectarFeed(simulacao.id, {
        aoReceberMensagem: (mensagem) => {
          setMensagens((atuais) => [...atuais, mensagem])
          setStatusTexto('As avaliações estão chegando...')
        },
        aoReceberParecer: (parecer) => {
          setPareceres((atuais) => [...atuais, parecer])
          setStatusTexto('As avaliações estão chegando...')
        },
        aoIniciarPesquisa: () => {
          setStatusTexto('O pesquisador está buscando preços e lojas parecidas na região...')
        },
        aoReceberPesquisa: (pesquisaRecebida) => {
          setPesquisa(pesquisaRecebida)
          setStatusTexto('Pesquisa de mercado concluída. Os agentes estão lendo as informações do produto...')
        },
        aoIniciarAnalise: () => {
          setStatusTexto('Todos avaliaram. O analista está juntando as opiniões, descartando exageros e escrevendo o relatório...')
        },
        aoFinalizar: (resultadoFinal) => {
          setMensagens(resultadoFinal.mensagens)
          setPareceres(resultadoFinal.pareceres ?? [])
          setResultado(resultadoFinal)
          setStatusTexto('Avaliação concluída. Preparando o panorama...')
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
    setPareceres([])
    setResultado(null)
    setPesquisa(null)
    setErroFeed('')
    setErroFormulario('')
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
    return <ResultPage personas={personasDaSimulacao} especialistas={especialistasDaSimulacao} resultado={resultado} onNovaAvaliacao={novaAvaliacao} />
  }

  if (tela === 'debate') {
    return (
      <DebatePage
        personas={personasDaSimulacao}
        especialistas={especialistasDaSimulacao}
        mensagens={mensagens}
        pareceres={pareceres}
        pesquisa={pesquisa}
        statusTexto={statusTexto}
        erro={erroFeed}
        onVoltar={novaAvaliacao}
      />
    )
  }

  return <HomePage personas={personas} especialistas={especialistas} carregando={carregando} erro={erroFormulario} aoAvaliar={avaliar} />
}
