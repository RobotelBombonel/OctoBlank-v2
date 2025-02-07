import json
import os
import sys
from datetime import datetime
from typing import List, Dict, Any
from gpt4all import GPT4All
import pygame

# Pygame GUI Setup
pygame.init()
WIDTH, HEIGHT = 850, 750
FONT = pygame.font.SysFont("Arial", 18)
INPUT_FONT = pygame.font.SysFont("Arial", 20)
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
GRAY = (200, 200, 200)
BLUE = (0, 120, 215)

screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("OctoBlank v2 Chat")

class ConversationManager:
    """Manages conversation history storage and retrieval"""
    
    def __init__(self, storage_path: str = 'dtb.json'):
        self.storage_path = storage_path
        self.history: List[Dict[str, Any]] = []
        self._load_history()
        
        self.model = GPT4All('orca-mini-3b-gguf2-q4_0.gguf')
        self.context_window = 2048
        self.max_history_messages = 1  # Single-turn mode
        
    def _load_history(self) -> None:
        try:
            if os.path.exists(self.storage_path):
                with open(self.storage_path, 'r') as f:
                    self.history = json.load(f)
        except Exception as e:
            print(f"Error loading history: {e}")
            self.history = []
            
    def _save_history(self) -> None:
        try:
            with open(self.storage_path, 'w') as f:
                json.dump(self.history, f, indent=2)
        except Exception as e:
            print(f"Error saving history: {e}")
            
    def add_message(self, role: str, content: str, save: bool = False) -> None:
        message = {
            'role': role,
            'content': content,
            'timestamp': datetime.now().isoformat(),
            'saved': save
        }
        self.history.append(message)
        if save:
            self._save_history()
        
    def delete_saved_memory(self) -> None:
        self.history = [msg for msg in self.history if not msg['saved']]
        self._save_history()
        
    def get_context_prompt(self) -> str:
        context = "You are OctoBlank v2. Important context:\n"
        context += "\n".join([f"{msg['role'].capitalize()}: {msg['content']}" 
                            for msg in self.history if msg['saved']])
        return context[:self.context_window] + "\n\nCurrent conversation:\n"
    
    def generate_response(self, user_input: str) -> str:
        prompt = self.get_context_prompt() + f"User: {user_input}\nOctoBlank:"
        try:
            with self.model.chat_session():
                response = self.model.generate(
                    prompt=prompt,
                    temp=0.9,  # More creative responses
                    top_k=50,  # Wider range of responses
                    max_tokens=500,
                    streaming=False
                )
            return response.strip()
        except Exception as e:
            return f"Error generating response: {str(e)}"

def wrap_text(text: str, font, max_width: int) -> List[str]:
    words = text.split(' ')
    lines = []
    current_line = ''
    for word in words:
        test_line = f"{current_line} {word}".strip()
        if font.size(test_line)[0] <= max_width:
            current_line = test_line
        else:
            lines.append(current_line)
            current_line = word
    if current_line:
        lines.append(current_line)
    return lines

def draw_rounded_rect(surface, color, rect, radius):
    pygame.draw.rect(surface, color, rect, border_radius=radius)

def draw_chat(screen, messages: List[str], input_text: str, input_box_height: int, scroll_offset: int):
    screen.fill(WHITE)
    y_offset = 20 - scroll_offset
    
    for msg in messages[-2:]:  # Single-turn display
        wrapped_lines = wrap_text(msg, FONT, WIDTH - 60)
        for line in wrapped_lines:
            if 20 <= y_offset <= HEIGHT - input_box_height - 50:
                text_surface = FONT.render(line, True, BLACK)
                screen.blit(text_surface, (30, y_offset))
            y_offset += 30

    input_lines = wrap_text(input_text, INPUT_FONT, WIDTH - 180)
    line_count = len(input_lines)
    input_box_height = max(60, 30 + (line_count * 25))
    
    input_rect = pygame.Rect(20, HEIGHT - input_box_height - 15, WIDTH - 150, input_box_height)
    draw_rounded_rect(screen, GRAY, input_rect, 15)
    
    for i, line in enumerate(input_lines):
        input_surface = INPUT_FONT.render(line, True, BLACK)
        screen.blit(input_surface, (30, HEIGHT - input_box_height - 10 + i * 25))
    
    send_rect = pygame.Rect(WIDTH - 120, HEIGHT - 65, 100, 45)
    draw_rounded_rect(screen, BLUE, send_rect, 10)
    send_text = FONT.render("SEND", True, WHITE)
    screen.blit(send_text, (WIDTH - 100, HEIGHT - 55))
    
    pygame.display.flip()

def main():
    bot = ConversationManager()
    messages = []
    input_text = ""
    input_box_height = 60
    scroll_offset = 0
    clock = pygame.time.Clock()
    
    while True:
        total_height = sum(len(wrap_text(msg, FONT, WIDTH - 60)) * 30 for msg in messages)
        max_scroll = max(0, total_height - (HEIGHT - input_box_height - 100))

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
                
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_RETURN:
                    if pygame.key.get_mods() & pygame.KMOD_CTRL:
                        user_input = input_text.strip().lower()
                        input_text = ""
                        input_box_height = 60
                        
                        if user_input == '/exit':
                            pygame.quit()
                            sys.exit()
                        elif user_input.startswith('/dmem'):
                            bot.delete_saved_memory()
                            messages = ["System: All saved memory deleted"]  # Single-turn reset
                        elif user_input.startswith('/save'):
                            parts = user_input.split('/save', 1)
                            content = parts[1].strip() if len(parts) > 1 else ""
                            if content:
                                bot.add_message('user', content, save=True)
                                messages = [f"System: Saved to memory: {content}"]  # Single-turn reset
                        else:
                            messages = []  # Clear previous messages
                            messages.append(f"You: {user_input}")
                            response = bot.generate_response(user_input)
                            messages.append(f"OctoBlank: {response}")
                    else:
                        input_text += '\n'
                elif event.key == pygame.K_BACKSPACE:
                    input_text = input_text[:-1]
                else:
                    input_text += event.unicode
                    
            if event.type == pygame.MOUSEBUTTONDOWN:
                mouse_pos = pygame.mouse.get_pos()
                if WIDTH - 120 <= mouse_pos[0] <= WIDTH - 20 and HEIGHT - 65 <= mouse_pos[1] <= HEIGHT - 20:
                    user_input = input_text.strip().lower()
                    input_text = ""
                    input_box_height = 60
                    
                    if user_input:
                        if user_input.startswith('/dmem'):
                            bot.delete_saved_memory()
                            messages = ["System: All saved memory deleted"]
                        elif user_input.startswith('/save'):
                            parts = user_input.split('/save', 1)
                            content = parts[1].strip() if len(parts) > 1 else ""
                            if content:
                                bot.add_message('user', content, save=True)
                                messages = [f"System: Saved to memory: {content}"]
                        else:
                            messages = []
                            messages.append(f"You: {user_input}")
                            response = bot.generate_response(user_input)
                            messages.append(f"OctoBlank: {response}")
        
        draw_chat(screen, messages, input_text, input_box_height, scroll_offset)
        clock.tick(60)

if __name__ == "__main__":
    main()