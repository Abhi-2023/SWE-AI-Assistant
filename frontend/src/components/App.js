import React, { useState } from 'react'
import Sidebar from '../components/Sidebar'
import Chat from '../pages/Chat'
import './App.css'

export default function App() {
  const [selectedNamespace, setNamespace]   = useState(null)
  const [selectedConv,      setSelectedConv] = useState(null)
  const [refreshTrigger,    setRefresh]      = useState(0)

  const handleNewChat = () => {
    setSelectedConv(null)
  }

  const handleConvCreated = () => {
    setRefresh(n => n + 1)
  }

  return (
    <div className="app-shell">
      <Sidebar
        selectedNamespace  = {selectedNamespace}
        onNamespaceChange  = {setNamespace}
        selectedConv       = {selectedConv}
        onSelectConv       = {setSelectedConv}
        onNewChat          = {handleNewChat}
        refreshTrigger     = {refreshTrigger}
      />
      <Chat
        conversationId       = {selectedConv}
        selectedNamespace    = {selectedNamespace}
        onConversationCreated = {handleConvCreated}
      />
    </div>
  )
}
