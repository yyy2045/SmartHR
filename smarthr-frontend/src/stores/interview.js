import { defineStore } from 'pinia'

export const useInterviewStore = defineStore('interview', {
  state: () => ({
    currentSession: null,
    messages: [],
    currentQuestion: null,
    skillScores: {},
    behaviorScores: {},
    isComplete: false,
    isLoading: false
  }),

  actions: {
    setSession(session) {
      this.currentSession = session
    },

    addMessage(message) {
      this.messages.push(message)
    },

    setQuestion(question) {
      this.currentQuestion = question
    },

    updateSkillScores(scores) {
      this.skillScores = { ...this.skillScores, ...scores }
    },

    updateBehaviorScores(scores) {
      this.behaviorScores = { ...this.behaviorScores, ...scores }
    },

    setComplete(complete) {
      this.isComplete = complete
    },

    reset() {
      this.currentSession = null
      this.messages = []
      this.currentQuestion = null
      this.skillScores = {}
      this.behaviorScores = {}
      this.isComplete = false
      this.isLoading = false
    }
  }
})