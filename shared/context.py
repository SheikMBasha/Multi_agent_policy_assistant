class ConversationContext:
    def __init__(self):
        self.state = {}

    def update(self, key, value):
        self.state[key] = value

    def get(self, key, default=None):
        return self.state.get(key, default)

    def clear(self):
        self.state.clear()

    def to_dict(self):
        return self.state

# ✅ Add this instance at the bottom
shared_context = ConversationContext()
