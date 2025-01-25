import pygame


class Button:
    def __init__(self, id: str, label: str, tooltip: str, x: int, y: int, width: int, height: int, color: str = "#333333", hover_color: str = "#444444"):
        self.id = id
        self.label = label
        self.tooltip = tooltip
        self.rect = pygame.Rect(x, y, width, height)
        self.color = color
        self.hover_color = hover_color
        self.font = pygame.font.Font(None, 20)
        self.text = self.font.render(self.label, True, (255, 255, 255))
        self.text_rect = self.text.get_rect(center=self.rect.center)

        self.fade_duration = 500
        self.fade_start_time = None
        self.is_hovered_now = False
        self.alpha = 0
        
        self.tooltip_alpha = 0
        self.tooltip_fade_start_time = None
        
    def draw(self, screen, mouse_pos):

        pygame.draw.rect(screen, self.hover_color if self.is_hovered(mouse_pos) else self.color, self.rect, border_radius=5)

        screen.blit(self.text, self.text_rect)
        
    def update_rect(self, x, y):
        self.rect.x = x
        self.rect.y = y
        self.text_rect = self.text.get_rect(center=self.rect.center)

    def is_hovered(self, mouse_pos) -> bool:
        return self.rect.collidepoint(mouse_pos)

    def show_tooltip(self, screen):
        tooltip_text = pygame.font.Font(None, 18).render(self.tooltip, True, (255, 255, 255))

        tooltip_bg = pygame.Surface((tooltip_text.get_width() + 10, tooltip_text.get_height() + 10), pygame.SRCALPHA)
        
        tooltip_bg.fill((0, 0, 0, 100))

        tooltip_x = self.rect.x + (self.rect.width - tooltip_bg.get_width()) // 2
        tooltip_y = self.rect.y - tooltip_bg.get_height() - 5

        screen.blit(tooltip_bg, (tooltip_x, tooltip_y))
        screen.blit(tooltip_text, (tooltip_x + 5, tooltip_y + 5))

class ButtonGroup:
    def __init__(self, controls_rect, background_color="#111111", padding: int = 10):
        self.buttons = []
        self.controls_rect = controls_rect
        self.background_color = background_color
        self.padding = padding

    def add_button(self, id: str, label: str, tooltip: str):
        self.buttons.append(Button(id, label, tooltip, 0, 0, 0, 0))
        self.update_buttons()

    def remove_button(self, label):
        self.buttons = [button for button in self.buttons if button.label != label]
        self.update_buttons()

    def update_buttons(self):
        total_space = self.controls_rect.width - (2 * self.padding) - (self.padding * (len(self.buttons) - 1))
        
        if len(self.buttons) > 0:
            button_width = total_space // len(self.buttons)
        else:
            button_width = 0
        
        button_height = self.controls_rect.height // 12

        for i, button in enumerate(self.buttons):
            button_x = self.controls_rect.x + self.padding + i * (button_width + self.padding)
            
            button.update_rect(button_x, self.controls_rect.y + self.controls_rect.height - button_height - self.padding)
            button.rect.width = button_width
            button.rect.height = button_height

    def draw(self, screen, mouse_pos):
            #pygame.draw.rect(screen, self.background_color, self.controls_rect)

            for button in self.buttons:
                button.draw(screen, mouse_pos)

                if button.is_hovered(mouse_pos):
                    button.show_tooltip(screen)