// pages/index.tsx
import React, { useState } from 'react';
import ChatHeader from '../components/ChatHeader';
import ChatList from '../components/ChatList';
import ChatInput from '../components/ChatInput';
import { askNL } from '../lib/apiClient';

type Chat = {
  id: string;
  title: string;
  time: string;
  messages: { sender: string; text: string }[];
};

const ChatPage: React.FC = () => {
  const [chats, setChats] = useState<Chat[]>([]);
  const [currentChatId, setCurrentChatId] = useState<string | null>(null);
  const [showChatList, setShowChatList] = useState(false);
  const [darkMode, setDarkMode] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSend = async (message: string, file?: File) => {
    if (!message.trim()) return;

    let newChatId = currentChatId;

    if (!currentChatId) {
      newChatId = (chats.length + 1).toString();
      const newChatTime = new Date().toLocaleTimeString();
      const newChatTitle = message.substring(0, 20);

      const newChat: Chat = {
        id: newChatId,
        title: newChatTitle,
        time: newChatTime,
        messages: [{ sender: 'User', text: message }],
      };

      setChats([...chats, newChat]);
      setCurrentChatId(newChatId);
    } else {
      setChats(prevChats =>
        prevChats.map(chat =>
          chat.id === currentChatId
            ? { ...chat, messages: [...chat.messages, { sender: 'User', text: message }] }
            : chat
        )
      );
    }

    try {
      setLoading(true);
      setError(null);

      // 🔥 NEW API CALL (LLM + DB)
      const data = await askNL(message);

      setChats(prevChats =>
        prevChats.map(chat =>
          chat.id === newChatId
            ? {
                ...chat,
                messages: [...chat.messages, { sender: 'Bot', text: data.answer }],
              }
            : chat
        )
      );
    } catch (err: any) {
      console.error(err);
      setError(err.message || 'Failed to get reply from backend');
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = (id: string) => {
    setChats(chats.filter(chat => chat.id !== id));
    if (currentChatId === id) {
      setCurrentChatId(null);
    }
  };

  const handleDeleteAll = () => {
    setChats([]);
    setCurrentChatId(null);
  };

  const toggleChatList = () => {
    setShowChatList(prev => !prev);
  };

  const startNewChat = () => {
    setCurrentChatId(null);
  };

  const toggleDarkMode = () => {
    setDarkMode(prev => !prev);
  };

  const currentChat = chats.find(chat => chat.id === currentChatId);

  return (
    <div
      className={`relative h-screen flex flex-col ${
        darkMode
          ? 'bg-gradient-to-b from-[#21187a] via-[#6457d8] to-[#f5f5ff] text-white'
          : 'bg-gradient-to-b from-[#f5f5ff] via-[#f5f5ff] to-[#282264] text-[#21187a]'
      }`}
    >
      <ChatHeader
        title={currentChat ? currentChat.title : ''}
        onToggleChatList={toggleChatList}
        onNewChat={startNewChat}
        onToggleDarkMode={toggleDarkMode}
        darkMode={darkMode}
      />

      {showChatList && (
        <ChatList
          chats={chats}
          onDelete={handleDelete}
          onClose={toggleChatList}
          onSelectChat={setCurrentChatId}
          onDeleteAll={handleDeleteAll}
        />
      )}

      <div className={`flex-grow p-4 overflow-y-auto ${showChatList ? 'mr-80' : ''}`}>
        {!currentChat && (
          <div className="flex items-center justify-center h-full">
            <img
              src="/assets/Allianz_logo.jpg"
              alt="Logo"
              className="h-40 w-55 mix-blend-multiply"
            />
            <span className="font-bold text-8xl ml-4">FBS</span>
          </div>
        )}

        {currentChat && (
          <div className="mt-4">
            {loading && <p className="text-sm text-gray-400">Sending message…</p>}
            {error && <p className="text-sm text-red-400">Error: {error}</p>}

            {currentChat.messages.map((msg, index) => (
              <div
                key={index}
                className={`mt-2 p-4 rounded-lg ${
                  msg.sender === 'Bot'
                    ? darkMode
                      ? 'bg-gray-800 text-left'
                      : 'bg-gray-100 text-left'
                    : 'text-right'
                }`}
              >
                <p className="font-semibold mb-1">{msg.sender}:</p>
                <p>{msg.text}</p>
              </div>
            ))}
          </div>
        )}
      </div>

      <ChatInput
        onSend={handleSend}
        isChatListVisible={showChatList}
        darkMode={darkMode}
      />
    </div>
  );
};

export default ChatPage;
