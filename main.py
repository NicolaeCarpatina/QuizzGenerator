import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import random
import re
import os
import sys

# === CONFIGURABLE UI CONSTANTS ===
FONT_FAMILY = "Helvetica"
FONT_SIZE_QUESTION = 20
FONT_SIZE_OPTION = 18
FONT_SIZE_BUTTON = 14
FONT_SIZE_SMALL = 11

FONT_QUESTION = (FONT_FAMILY, FONT_SIZE_QUESTION, "bold")
FONT_OPTION = (FONT_FAMILY, FONT_SIZE_OPTION)
FONT_BUTTON = (FONT_FAMILY, FONT_SIZE_BUTTON)
FONT_SMALL = (FONT_FAMILY, FONT_SIZE_SMALL)
FONT_OPTION_BOLD = (FONT_FAMILY, FONT_SIZE_OPTION, "bold")

DEFAULT_MENU_SIZE = "500x300"
DEFAULT_QUIZ_SIZE = "1500x600"
WINDOW_SIZE_FILE = "window_size.cfg"

def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)


class Question:
    def __init__(self, text, options):
        self.text = text
        self.options = options  # List of (full_option_text, is_correct_boolean)
        self.shuffled_options = []  # List of (full_option_text, is_correct_boolean) - subset shown in quiz
        self.type = None


def parse_questions_from_file(file_path):
    questions = []
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        blocks = re.findall(r'(?s)(?m)^(\d+)\.\s*(.*?)(?=\n\d+\.\s*|\Z)', content.strip())

        for num_str, block_content in blocks:
            lines = block_content.strip().split('\n')
            if not lines:
                print(f"Warning: Block starting with {num_str}. has no content.")
                continue

            question_text = lines[0].strip()
            options = []
            for line in lines[1:]:
                match = re.match(r'^([a-j])\.\s+\[(y|x)]\s+(.*)', line.strip())
                if match:
                    letter, correctness, text = match.groups()
                    options.append((f"{letter}. {text.strip()}", correctness == 'y'))
            if options:
                full_question_text = f"{num_str}. {question_text}"
                questions.append(Question(full_question_text, options))
            elif question_text:
                print(f"Warning: Question '{num_str}. {question_text}' has no valid options and will be skipped.")

    except Exception as e:
        messagebox.showerror("Error loading file", f"Could not read or parse file: {e}")
        return []
    return questions


class QuizApp:
    def __init__(self, root):
        self.root = root
        self.root.iconbitmap(resource_path("new_icon.ico"))
        self.root.title("Nicolae's Quiz App")
        self.root.geometry(DEFAULT_MENU_SIZE)

        self.dark_mode = False
        self.default_fg_color = "#000000"
        self.disabled_fg_color = "#a3a3a3"  # Will be updated by configure_colors

        self.questions = []
        self.quiz_questions = []
        self.current_question_index = 0
        self.user_answers = []  # Stores lists of 0/1 for selected options, corresponds to shuffled_options
        self.score = 0
        self.max_score = 0
        self.scores_breakdown = []
        self.source_file_name = ""
        self.mode = 'menu'
        self.review_index = 0

        self.vars = []
        self.saved_vars = []

        self.timer_id = None
        self.elapsed_seconds = 0
        self.timer_label = None
        self.timer_running = False

        self.dark_mode_button = None

        self.setup_styles()
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.center_window()
        self.main_menu()

    def load_window_size(self):
        if os.path.exists(WINDOW_SIZE_FILE):
            try:
                with open(WINDOW_SIZE_FILE, "r") as f:
                    size = f.read().strip()
                    if 'x' in size:
                        return size
            except Exception:
                pass
        return DEFAULT_QUIZ_SIZE

    def save_window_size(self):
        try:
            size = f"{self.root.winfo_width()}x{self.root.winfo_height()}"
            with open(WINDOW_SIZE_FILE, "w") as f:
                f.write(size)
        except Exception as e:
            print(f"Error saving window size: {e}")

    def on_closing(self):
        self.save_window_size()
        self.stop_elapsed_timer()
        self.root.destroy()

    def center_window(self):
        self.root.update_idletasks()
        w = self.root.winfo_width()
        h = self.root.winfo_height()
        ws = self.root.winfo_screenwidth()
        hs = self.root.winfo_screenheight()
        x = (ws // 2) - (w // 2)
        y = (hs // 2) - (h // 2)
        self.root.geometry(f'{w}x{h}+{x}+{y}')

    def setup_styles(self):
        self.style = ttk.Style()
        self.style.theme_use("clam")
        self.configure_colors()

    def configure_colors(self):
        if self.dark_mode:
            bg = "#000000"
            fg = "#ffffff"
            entry_field_bg = "#000000"
            self.disabled_fg_color = "#888888"  # For dark mode
        else:
            bg = "#ffffff"
            fg = "#000000"
            entry_field_bg = "#ffffff"
            self.disabled_fg_color = "#a3a3a3"  # For light mode

        btn_fg = "#000000"
        self.default_fg_color = fg
        self.root.configure(bg=bg)

        self.style.configure("TFrame", background=bg, foreground=fg)
        self.style.configure("TLabel", background=bg, foreground=fg)
        self.style.configure("TCheckbutton", background=bg, foreground=fg)  # General TCheckbutton

        # Configure Quiz.TCheckbutton (for options in quiz)
        self.style.configure("Quiz.TCheckbutton", font=FONT_OPTION, background=bg, foreground=fg)
        if self.dark_mode:
            self.style.map("Quiz.TCheckbutton",
                           background=[('active', '#ffffff')],  # White background on hover
                           foreground=[('active', '#000000')])  # Black text on hover
        else:
            # For light mode, use theme's default hover or a subtle custom one
            # Ensuring map is specific to light mode or reset if dark mode had one
            default_active_bg = self.style.lookup("TCheckbutton", "background", ["active"])
            default_active_fg = self.style.lookup("TCheckbutton", "foreground", ["active"])
            self.style.map("Quiz.TCheckbutton",
                           background=[('active', default_active_bg if default_active_bg else "#f0f0f0")],  # Fallback
                           foreground=[('active', default_active_fg if default_active_fg else fg)])  # Fallback

        self.style.configure("TButton", foreground=btn_fg, font=FONT_BUTTON, padding=(10, 5))
        self.style.map("TButton",
                       foreground=[("disabled", self.disabled_fg_color),
                                   ("pressed", btn_fg),
                                   ("active", btn_fg)],
                       )

        self.style.configure("TEntry", fieldbackground=entry_field_bg, foreground=fg, insertcolor=fg)

        if self.dark_mode:
            self.style.configure("Vertical.TScrollbar", troughcolor="#333333", background="#555555",
                                 arrowcolor="#ffffff")
            self.style.map("Vertical.TScrollbar", background=[('active', '#777777')])
        else:
            self.style.configure("Vertical.TScrollbar", troughcolor="#f0f0f0", background="#d3d3d3",
                                 arrowcolor="#000000")
            self.style.map("Vertical.TScrollbar", background=[('active', '#c0c0c0')])

    def toggle_theme(self):
        if self.mode == 'menu':
            return

        if self.mode == 'quiz':
            self.save_current_checkbox_states()

        self.dark_mode = not self.dark_mode
        self.configure_colors()
        if self.mode == 'quiz':
            self.show_question(preserve_vars=True)
        elif self.mode == 'review':
            self.review_question(self.review_index)
        elif self.mode == 'score':
            self.show_score()

    def save_current_checkbox_states(self):
        if self.vars:
            self.saved_vars = [var.get() for var in self.vars]
        else:
            self.saved_vars = []

    def add_dark_mode_button(self):
        if self.dark_mode_button and self.dark_mode_button.winfo_exists():
            self.dark_mode_button.destroy()
            self.dark_mode_button = None

        if self.mode != 'menu':
            btn_text = " 🌙 " if not self.dark_mode else " ☀ "
            self.dark_mode_button = ttk.Button(self.root, text=btn_text, command=self.toggle_theme, style="TButton",
                                               takefocus=0, state='normal')
            self.dark_mode_button.place(relx=1.0, rely=0.0, anchor="ne", x=-10, y=10)

    def main_menu(self):
        self.mode = 'menu'
        self.stop_elapsed_timer()
        for widget in self.root.winfo_children():
            widget.destroy()

        if self.source_file_name:
            label_text = f"📁 File: {os.path.basename(self.source_file_name)}"
            if self.questions:
                label_text += f" ({len(self.questions)} questions)"
            label = ttk.Label(self.root, text=label_text, anchor="e", font=FONT_SMALL)
            label.pack(pady=5, padx=10, fill='x')

        main_frame = ttk.Frame(self.root)
        main_frame.pack(expand=True, fill='both', padx=20, pady=10)

        ttk.Button(main_frame, text="📂 Load Quiz File", command=self.load_file, style="TButton", takefocus=0).pack(
            pady=8, fill='x')

        num_q_frame = ttk.Frame(main_frame)
        num_q_frame.pack(pady=8, fill='x')
        num_q_frame.columnconfigure(0, weight=1)
        num_q_frame.columnconfigure(1, weight=0)
        num_q_frame.columnconfigure(2, weight=1)

        ttk.Label(num_q_frame, text="How many questions?", font=FONT_BUTTON).grid(row=0, column=1, sticky='ew')

        if not hasattr(self, 'num_questions_var'):
            self.num_questions_var = tk.IntVar()

        default_q_val = 5
        if self.questions:
            default_q_val = min(5, len(self.questions))
            if hasattr(self,
                       'num_questions_var') and self.num_questions_var.get() > 0 and self.num_questions_var.get() <= len(
                self.questions):
                default_q_val = self.num_questions_var.get()
        elif hasattr(self, 'num_questions_var') and self.num_questions_var.get() > 0:
            default_q_val = self.num_questions_var.get()
        else:
            default_q_val = 5 if len(self.questions) == 0 else min(5, len(self.questions))

        self.num_questions_var.set(default_q_val)
        self.num_questions_entry = ttk.Entry(num_q_frame, textvariable=self.num_questions_var, width=5,
                                             font=FONT_BUTTON, justify='center')
        self.num_questions_entry.grid(row=1, column=1, pady=4)

        state = 'normal' if self.questions else 'disabled'
        self.start_btn = ttk.Button(main_frame, text="Start Quiz", command=self.start_quiz, state=state,
                                    style="TButton", takefocus=0)
        self.start_btn.pack(pady=8, fill='x')

    def load_file(self):
        file_path = filedialog.askopenfilename(filetypes=[("Text files", "*.txt")])
        if file_path:
            loaded_questions = parse_questions_from_file(file_path)
            if loaded_questions:
                self.questions = loaded_questions
                self.source_file_name = file_path
                messagebox.showinfo("Success", f"{len(self.questions)} questions loaded.")
                if hasattr(self, 'num_questions_var'):
                    self.num_questions_var.set(min(5, len(self.questions)))
                self.main_menu()
            else:
                self.questions = []
                self.source_file_name = ""
                if hasattr(self, 'num_questions_var'):
                    self.num_questions_var.set(5)
                messagebox.showerror("Loading Error", "No valid questions found in the selected file or file is empty.")
                self.main_menu()

    def start_quiz(self):
        try:
            num = self.num_questions_var.get()
            if not isinstance(num, int) or num <= 0:
                raise ValueError("Number of questions must be a positive integer.")
        except (tk.TclError, ValueError):
            messagebox.showerror("Error", "Please enter a valid positive number for questions.")
            return

        if not self.questions:
            messagebox.showerror("Error", "No questions loaded. Please load a quiz file first.")
            return

        if not (0 < num <= len(self.questions)):
            messagebox.showerror("Error", f"Please choose a number of questions between 1 and {len(self.questions)}.")
            return

        self.root.geometry(self.load_window_size())
        self.center_window()
        num_to_sample = min(num, len(self.questions))
        self.quiz_questions = random.sample(self.questions, num_to_sample)

        for q in self.quiz_questions:
            if not q.options:
                q.shuffled_options = []
                q.type = 'CS'  # Or handle as error/skip
                continue

            correct_opts = [opt for opt in q.options if opt[1]]
            incorrect_opts = [opt for opt in q.options if not opt[1]]

            q.type = 'CS' if correct_opts and random.choice([True, False]) else 'CM'
            if not correct_opts: q.type = 'CM'  # Default to CM if no correct options (edge case)

            if q.type == 'CS':
                # Ensure at least one correct option is chosen if available
                if correct_opts:
                    chosen_correct = random.sample(correct_opts, 1)  # Take one correct
                    num_incorrect_needed = 4  # Aim for 1 correct + 4 incorrect = 5 total
                    num_incorrect_to_sample = min(num_incorrect_needed, len(incorrect_opts))
                    sampled_incorrect = random.sample(incorrect_opts, num_incorrect_to_sample)
                    q.shuffled_options = chosen_correct + sampled_incorrect
                else:  # No correct options, take some incorrect ones
                    q.shuffled_options = random.sample(incorrect_opts, min(5, len(incorrect_opts)))
                random.shuffle(q.shuffled_options)
            else:  # CM Type
                num_total_options_target = 5
                # Ensure at least 2 correct if available, up to 4 for CM
                min_correct_for_cm = min(len(correct_opts), 2) if len(correct_opts) >= 2 else len(correct_opts)
                max_correct_for_cm = min(len(correct_opts), 4)

                num_correct_selected = 0
                if max_correct_for_cm > 0:  # Ensure min_correct_for_cm <= max_correct_for_cm
                    num_correct_selected = random.randint(min_correct_for_cm, max_correct_for_cm)

                chosen_correct = random.sample(correct_opts, num_correct_selected)
                num_incorrect_needed = num_total_options_target - num_correct_selected
                num_incorrect_to_sample = min(num_incorrect_needed, len(incorrect_opts))
                sampled_incorrect = random.sample(incorrect_opts, num_incorrect_to_sample)
                q.shuffled_options = chosen_correct + sampled_incorrect

                # Fill up to 5 if possible with more incorrect options
                if len(q.shuffled_options) < num_total_options_target and len(incorrect_opts) > num_incorrect_to_sample:
                    remaining_slots = num_total_options_target - len(q.shuffled_options)
                    additional_incorrect_options = [opt for opt in incorrect_opts if opt not in sampled_incorrect]
                    additional_incorrect = random.sample(
                        additional_incorrect_options,
                        min(remaining_slots, len(additional_incorrect_options))
                    )
                    q.shuffled_options.extend(additional_incorrect)
                random.shuffle(q.shuffled_options)

                # Fallback if still no options (e.g. very few original options)
                if not q.shuffled_options and q.options:
                    q.shuffled_options = random.sample(q.options, min(num_total_options_target, len(q.options)))
                    random.shuffle(q.shuffled_options)

        self.current_question_index = 0
        self.user_answers = [[] for _ in self.quiz_questions]
        self.score = 0
        self.max_score = len(self.quiz_questions) * 5 if self.quiz_questions else 0
        self.scores_breakdown = [0] * len(self.quiz_questions)
        self.saved_vars = []
        self.elapsed_seconds = 0
        self.show_question()

    def show_question(self, preserve_vars=False):
        self.mode = 'quiz'
        self.stop_elapsed_timer()
        for widget in self.root.winfo_children():
            widget.destroy()

        self.add_dark_mode_button()

        if not (0 <= self.current_question_index < len(self.quiz_questions)):
            self.stop_elapsed_timer()
            self.calculate_score()
            self.show_score()
            return

        # This frame will hold the centered labels
        top_info_frame = ttk.Frame(self.root)
        top_info_frame.pack(fill='x', pady=(10, 0), padx=20)

        # Timer Label (packed first to appear on top)
        self.timer_label = ttk.Label(top_info_frame, text="", font=FONT_BUTTON)
        self.timer_label.pack(pady=(0, 2))  # .pack() centers it horizontally by default
        self.start_elapsed_timer()

        # Question Number Label (packed second to appear below timer)
        question_number_text = f"Question {self.current_question_index + 1} of {len(self.quiz_questions)}"
        question_number_label = ttk.Label(top_info_frame, text=question_number_text, font=FONT_BUTTON)
        question_number_label.pack(pady=(0, 5))

        q = self.quiz_questions[self.current_question_index]
        question_label_wraplength = max(300, self.root.winfo_width() - 40)
        ttk.Label(self.root, text=f"[{q.type}] {q.text}",
                  wraplength=question_label_wraplength, justify="left",
                  font=FONT_QUESTION).pack(pady=20, anchor='w', padx=20)

        options_frame = ttk.Frame(self.root)
        options_frame.pack(fill='both', expand=True, padx=20, pady=10)
        self.vars = []
        self.checkbuttons = []

        def update_font(index):
            var = self.vars[index]
            cb = self.checkbuttons[index]
            cb.config(font=FONT_OPTION_BOLD if var.get() else FONT_OPTION)

        if not q.shuffled_options:
            ttk.Label(options_frame, text="No options available for this question.", font=FONT_OPTION).pack(anchor='w',
                                                                                                            padx=40,
                                                                                                            pady=4)
        else:
            for i, (opt_text, _) in enumerate(q.shuffled_options):
                var = tk.IntVar(value=0)

                match = re.match(r"^[a-j]\.\s*(.*)", opt_text)
                cb_text = match.group(1) if match else opt_text

                cb = tk.Checkbutton(options_frame, text=cb_text, variable=var,
                                    font=FONT_OPTION, anchor='w', justify='left',
                                    bg=self.root["bg"], fg=self.default_fg_color,
                                    selectcolor=self.root["bg"],
                                    activebackground=self.root["bg"],
                                    activeforeground=self.default_fg_color,
                                    command=lambda idx=i: update_font(idx))
                cb.pack(anchor='w', padx=40, pady=4)
                self.vars.append(var)
                self.checkbuttons.append(cb)

        if preserve_vars:
            if self.current_question_index < len(self.user_answers) and self.user_answers[self.current_question_index]:
                current_answers = self.user_answers[self.current_question_index]
                for i, var_value in enumerate(current_answers):
                    if i < len(self.vars):
                        self.vars[i].set(var_value)
                        self.checkbuttons[i].config(font=FONT_OPTION_BOLD if var_value else FONT_OPTION)
            elif self.saved_vars:
                for i, var_value in enumerate(self.saved_vars):
                    if i < len(self.vars):
                        self.vars[i].set(var_value)
                        self.checkbuttons[i].config(font=FONT_OPTION_BOLD if var_value else FONT_OPTION)
            self.saved_vars = []

        nav_frame = ttk.Frame(self.root)
        nav_frame.pack(side='bottom', fill='x', padx=20, pady=20)
        nav_frame.columnconfigure(0, weight=1)
        nav_frame.columnconfigure(1, weight=0)
        nav_frame.columnconfigure(2, weight=1)  # Spacer column
        nav_frame.columnconfigure(3, weight=0)
        nav_frame.columnconfigure(4, weight=1)

        next_btn = ttk.Button(nav_frame, text="Next", command=self.next_question, style="TButton", takefocus=0)
        next_btn.grid(row=0, column=3, padx=10)
        if self.current_question_index > 0:
            prev_btn = ttk.Button(nav_frame, text="Previous", command=self.prev_question, style="TButton",
                                  takefocus=0)
            prev_btn.grid(row=0, column=1, padx=10)

        # --- FIX: Lift the dark mode button to the top of the stacking order ---
        if self.dark_mode_button:
            self.dark_mode_button.lift()

    def next_question(self):
        while len(self.user_answers) <= self.current_question_index:
            self.user_answers.append([])
        self.user_answers[self.current_question_index] = [var.get() for var in self.vars]
        self.saved_vars = []
        self.current_question_index += 1
        if self.current_question_index >= len(self.quiz_questions):
            self.stop_elapsed_timer()
            self.calculate_score()
            self.show_score()
        else:
            self.show_question(preserve_vars=True)

    def prev_question(self):
        while len(self.user_answers) <= self.current_question_index:
            self.user_answers.append([])
        self.user_answers[self.current_question_index] = [var.get() for var in self.vars]
        self.saved_vars = []
        if self.current_question_index > 0:
            self.current_question_index -= 1
            self.show_question(preserve_vars=True)

    def calculate_score(self):
        self.score = 0
        for q_index, q in enumerate(self.quiz_questions):
            if not q.shuffled_options:
                self.scores_breakdown[q_index] = 0
                continue

            shuffled_correct_flags = [opt_tuple[1] for opt_tuple in q.shuffled_options]
            num_presented_options = len(shuffled_correct_flags)

            user_flags_for_q = []
            if q_index < len(self.user_answers) and self.user_answers[q_index]:
                user_flags_for_q = self.user_answers[q_index][:]
                while len(user_flags_for_q) < num_presented_options: user_flags_for_q.append(0)
                user_flags_for_q = user_flags_for_q[:num_presented_options]
            else:
                user_flags_for_q = [0] * num_presented_options

            q_score = 0
            user_selected_shuffled_indices = [i for i, is_selected in enumerate(user_flags_for_q) if is_selected]

            true_correct_texts_in_shuffled = [
                opt_text for opt_text, is_correct_in_original in q.shuffled_options if is_correct_in_original
            ]

            if q.type == 'CS':
                if len(user_selected_shuffled_indices) == 1:
                    selected_option_text = q.shuffled_options[user_selected_shuffled_indices[0]][0]
                    if selected_option_text in true_correct_texts_in_shuffled:
                        q_score = 5
            else:  # CM
                if not (2 <= len(user_selected_shuffled_indices) <= 4):
                    q_score = 0
                else:
                    q_score = 5
                    for i in range(num_presented_options):
                        is_option_originally_correct = q.shuffled_options[i][1]
                        if (user_flags_for_q[i] and not is_option_originally_correct) or \
                                (not user_flags_for_q[i] and is_option_originally_correct):
                            q_score -= 1
                    q_score = max(0, q_score)
                    q_score = min(q_score, 5)

            self.scores_breakdown[q_index] = q_score
            self.score += q_score

    def show_score(self):
        self.mode = 'score'
        self.stop_elapsed_timer()
        for widget in self.root.winfo_children():
            widget.destroy()
        self.add_dark_mode_button()

        ttk.Label(self.root, text="Quiz Complete!", font=FONT_QUESTION).pack(pady=20)
        actual_max_score = len(self.quiz_questions) * 5 if self.quiz_questions else 0
        ttk.Label(self.root, text=f"Total Score: {self.score} / {actual_max_score} points",
                  font=(FONT_FAMILY, 20, "bold")).pack(pady=5)
        final_grade = (self.score / actual_max_score) * 9 + 1 if actual_max_score > 0 else 1.0
        ttk.Label(self.root, text=f"Final grade: {final_grade:.2f} / {10}", font=(FONT_FAMILY, 20, "bold")).pack(pady=5)

        hours, remainder = divmod(self.elapsed_seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        time_parts = []
        if hours > 0: time_parts.append(f"{hours}h")
        if minutes > 0 or hours > 0: time_parts.append(f"{minutes}m")
        time_parts.append(f"{seconds}s")
        time_str = " ".join(time_parts) if time_parts else "0s"
        ttk.Label(self.root, text=f"Total Time: {time_str}", font=FONT_BUTTON).pack(pady=5)

        buttons_frame = ttk.Frame(self.root)
        buttons_frame.pack(pady=20, fill='x', padx=max(50, int(self.root.winfo_width() * 0.1)))
        review_state = 'normal' if self.quiz_questions else 'disabled'
        ttk.Button(buttons_frame, text="🔍 Review Answers", command=lambda: self.review_question(0), style="TButton",
                   takefocus=0, state=review_state).pack(pady=10, fill='x')
        start_another_state = 'normal' if self.questions else 'disabled'
        ttk.Button(buttons_frame, text="🔄 Start Another Quiz", command=self.start_another_quiz, style="TButton",
                   takefocus=0, state=start_another_state).pack(pady=10, fill='x')
        ttk.Button(buttons_frame, text="🏠 Back to Menu", command=self.back_to_menu, style="TButton", takefocus=0).pack(
            pady=10, fill='x')

        # --- FIX: Lift the dark mode button to the top of the stacking order ---
        if self.dark_mode_button:
            self.dark_mode_button.lift()

    def review_question(self, index):
        self.mode = 'review'
        self.stop_elapsed_timer()
        self.review_index = index
        for widget in self.root.winfo_children():
            widget.destroy()
        self.add_dark_mode_button()

        if not (0 <= index < len(self.quiz_questions)):
            self.show_score()
            return

        q = self.quiz_questions[index]
        question_label_wraplength = max(300, self.root.winfo_width() - 40)
        ttk.Label(self.root, text=f"[{q.type}] {q.text}", wraplength=question_label_wraplength, justify="left",
                  font=FONT_QUESTION).pack(pady=20, anchor='w', padx=20)

        label_bg_color = self.root.cget('bg')
        default_review_fg_color = self.default_fg_color
        content_frame = ttk.Frame(self.root)
        content_frame.pack(fill='both', expand=True, padx=20, pady=10)
        content_bg_color = self.root.cget('bg')

        presented_option_texts = {opt_tuple[0] for opt_tuple in q.shuffled_options} if q.shuffled_options else set()

        user_selections_for_presented_options = {}
        if q.shuffled_options and index < len(self.user_answers) and self.user_answers[index]:
            current_q_user_selections = self.user_answers[index]
            for i, (opt_text, _) in enumerate(q.shuffled_options):
                if i < len(current_q_user_selections):
                    user_selections_for_presented_options[opt_text] = current_q_user_selections[i]
                else:
                    user_selections_for_presented_options[opt_text] = 0

        if not q.options:
            tk.Label(content_frame, text="No original options were defined for this question.", font=FONT_OPTION,
                     bg=content_bg_color, fg=default_review_fg_color).pack(anchor='w', padx=40, pady=2)
        else:
            for original_opt_text, is_original_correct in q.options:
                mark = ""
                text_color_for_option = default_review_fg_color
                display_text_suffix = ""

                if original_opt_text in presented_option_texts:
                    selected_by_user = user_selections_for_presented_options.get(original_opt_text, 0)

                    if is_original_correct and selected_by_user:
                        mark = "✅"
                        text_color_for_option = "green"
                    elif not is_original_correct and selected_by_user:
                        mark = "❌"
                        text_color_for_option = "red"
                    elif is_original_correct and not selected_by_user:
                        mark = "🟠"
                        text_color_for_option = "orange"
                    elif not is_original_correct and not selected_by_user:
                        mark = ""
                else:
                    mark = ""
                    text_color_for_option = self.disabled_fg_color
                    display_text_suffix = ""

                full_display_text = f"{mark} {original_opt_text}{display_text_suffix}"
                lbl = tk.Label(content_frame, text=full_display_text, font=FONT_OPTION, fg=text_color_for_option,
                               bg=content_bg_color, anchor='w', justify='left')
                lbl.pack(anchor='w', padx=40, pady=2)

        def create_legend_label(parent, text_symbol, specific_fg_color):
            lbl = tk.Label(parent, text=text_symbol, font=FONT_SMALL, fg=specific_fg_color, bg=label_bg_color)
            lbl.pack(side='left', padx=6)

        legend_frame = ttk.Frame(self.root)
        legend_frame.pack(pady=(0, 10), padx=20, anchor='w', fill='x')
        create_legend_label(legend_frame, "✅ Correct", "green")
        create_legend_label(legend_frame, "❌ Wrong", "red")
        create_legend_label(legend_frame, "🟠 Missed", "orange")
        create_legend_label(legend_frame, f"Not presented", self.disabled_fg_color)

        q_score_breakdown = self.scores_breakdown[index] if index < len(self.scores_breakdown) else 0
        max_q_score = 5
        ttk.Label(content_frame, text=f"Score for this question: {q_score_breakdown} / {max_q_score}",
                  font=(FONT_FAMILY, 14, "bold")).pack(pady=12)

        nav_frame = ttk.Frame(self.root)
        nav_frame.pack(side='bottom', fill='x', padx=20, pady=20)
        nav_frame.columnconfigure(0, weight=1)
        nav_frame.columnconfigure(1, weight=0)
        nav_frame.columnconfigure(2, weight=1)
        nav_frame.columnconfigure(3, weight=0)
        nav_frame.columnconfigure(4, weight=1)

        if index > 0:
            prev_btn = ttk.Button(nav_frame, text="Previous", command=lambda: self.review_question(index - 1),
                                  style="TButton", takefocus=0)
            prev_btn.grid(row=0, column=1, padx=10, sticky='e')
        score_btn = ttk.Button(nav_frame, text="Back to Score", command=self.show_score, style="TButton", takefocus=0)
        score_btn.grid(row=0, column=2, padx=10, sticky='nsew')
        if index < len(self.quiz_questions) - 1:
            next_btn = ttk.Button(nav_frame, text="Next", command=lambda: self.review_question(index + 1),
                                  style="TButton", takefocus=0)
            next_btn.grid(row=0, column=3, padx=10, sticky='w')

        # --- FIX: Lift the dark mode button to the top of the stacking order ---
        if self.dark_mode_button:
            self.dark_mode_button.lift()

    def start_another_quiz(self):
        self.root.geometry(DEFAULT_MENU_SIZE)  # Reset to menu size
        self.center_window()
        self.main_menu()  # Go back to main menu to select number of questions

    def back_to_menu(self):
        self.root.geometry(DEFAULT_MENU_SIZE)  # Reset to menu size
        self.center_window()
        self.main_menu()

    def stop_elapsed_timer(self):
        if self.timer_id:
            self.root.after_cancel(self.timer_id)
            self.timer_id = None
        self.timer_running = False

    def update_elapsed_time(self):
        if not self.timer_running: return
        self.elapsed_seconds += 1
        hours, remainder = divmod(self.elapsed_seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        time_str = ""
        if hours > 0: time_str += f"{hours:02d}h:"
        if minutes > 0 or hours > 0: time_str += f"{minutes:02d}m:"
        time_str += f"{seconds:02d}s"

        if self.timer_label and self.timer_label.winfo_exists():
            self.timer_label.config(text=f"Time: {time_str}")
        self.timer_id = self.root.after(1000, self.update_elapsed_time)

    def start_elapsed_timer(self):
        self.stop_elapsed_timer()  # Ensure no multiple timers
        self.timer_running = True
        self.update_elapsed_time()  # Start immediately


if __name__ == '__main__':
    root = tk.Tk()
    app = QuizApp(root)
    root.mainloop()