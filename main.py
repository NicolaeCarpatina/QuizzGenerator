import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import random
import re
import os

# === CONFIGURABLE UI CONSTANTS ===
FONT_FAMILY = "Helvetica"
FONT_SIZE_QUESTION = 16
FONT_SIZE_OPTION = 18
FONT_SIZE_BUTTON = 14
FONT_SIZE_SMALL = 11

FONT_QUESTION = (FONT_FAMILY, FONT_SIZE_QUESTION)
FONT_OPTION = (FONT_FAMILY, FONT_SIZE_OPTION)
FONT_BUTTON = (FONT_FAMILY, FONT_SIZE_BUTTON)
FONT_SMALL = (FONT_FAMILY, FONT_SIZE_SMALL)

DEFAULT_MENU_SIZE = "500x300"
DEFAULT_QUIZ_SIZE = "1500x600"


class Question:
    def __init__(self, text, options):
        self.text = text
        self.options = options
        self.shuffled_options = []
        self.type = None


def parse_questions_from_file(file_path):
    questions = []
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Regex to find blocks starting with a number followed by a dot and space
        # Use re.DOTALL to make '.' match newlines, allowing the regex to span lines
        # Capture the number and the content following it until the next numbered block or end of string
        # Added r'(?m)^' to anchor the start of the match to the beginning of a line in multiline mode
        blocks = re.findall(r'(?s)(?m)^(\d+)\.\s*(.*?)(?=\n\d+\.\s*|\Z)', content.strip())

        for num_str, block_content in blocks:
            lines = block_content.strip().split('\n')
            if not lines:
                print(f"Warning: Block starting with {num_str}. has no content.")
                continue

            # The first line after the number is the question text
            question_text = lines[0].strip()
            options = []
            # Process subsequent lines for options
            for line in lines[1:]:
                # Added ^ to anchor match to the start of the line (after strip)
                match = re.match(r'^([a-j])\.\s+\[(y|x)]\s+(.*)', line.strip())
                if match:
                    letter, correctness, text = match.groups()
                    options.append((f"{letter}. {text.strip()}", correctness == 'y'))  # Strip text too
            if options:
                # Add question number and text to the Question object for display
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
        self.root.title("Nicolae's Quiz App")
        self.root.geometry(DEFAULT_MENU_SIZE)

        self.dark_mode = False
        self.default_fg_color = "#000000"  # Initialize, will be set correctly in configure_colors

        self.questions = []
        self.quiz_questions = []
        self.current_question_index = 0
        self.user_answers = []
        self.score = 0
        self.max_score = 0
        self.scores_breakdown = []
        self.source_file_name = ""
        self.mode = 'menu'  # Start in menu mode
        self.review_index = 0

        self.vars = []
        self.saved_vars = []

        self.timer_id = None
        self.elapsed_seconds = 0
        self.timer_label = None
        self.timer_running = False

        self.dark_mode_button = None  # Keep a reference to the button

        self.setup_styles()
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.center_window()
        self.main_menu()  # This will build the menu *without* the dark mode button initially

    def on_closing(self):
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
        # Define general background and foreground based on dark_mode
        if self.dark_mode:
            bg = "#000000"  # Black background
            fg = "#ffffff"  # White foreground for general text (Labels, Checkbuttons etc.)
            entry_field_bg = "#000000"
            disabled_fg = "#888888"  # Grey for disabled text
        else:
            bg = "#ffffff"  # White background
            fg = "#000000"  # Black foreground for general text
            entry_field_bg = "#ffffff"
            disabled_fg = "#a3a3a3"  # Grey for disabled text

        # Define button foreground specifically
        # Request is to keep button text black in dark mode
        btn_fg = "#000000"  # Black button text in all modes

        # Store the general foreground color for use in tk.Labels (like in review)
        self.default_fg_color = fg

        self.root.configure(bg=bg)
        # Apply general colors to TFrame, TLabel, TCheckbutton
        self.style.configure("TFrame", background=bg, foreground=fg)
        self.style.configure("TLabel", background=bg, foreground=fg)
        self.style.configure("TCheckbutton", background=bg, foreground=fg)
        self.style.configure("Quiz.TCheckbutton", font=FONT_OPTION)  # Keep custom font

        # --- Keep Button Borders and Set Black Text ---
        # Use btn_fg for the normal state foreground
        self.style.configure("TButton", foreground=btn_fg, font=FONT_BUTTON, padding=(10, 5))
        self.style.map("TButton",
                       # Use disabled_fg for the disabled state text
                       # Use btn_fg for the active and pressed states text
                       foreground=[("disabled", disabled_fg),
                                   ("pressed", btn_fg),  # Set pressed state text to black
                                   ("active", btn_fg)],  # Set active state text to black
                       # Removed background mapping to let theme handle it for borders
                       # Removed relief mapping to let theme handle it for borders
                       )

        # Apply colors to TEntry
        self.style.configure("TEntry", fieldbackground=entry_field_bg, foreground=fg, insertcolor=fg)

        # Configure Scrollbar colors
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

        # If in quiz mode, save current selections before clearing the screen
        if self.mode == 'quiz':
            self.save_current_checkbox_states()

        self.dark_mode = not self.dark_mode
        self.configure_colors()
        # Rebuild the current screen after changing theme
        if self.mode == 'quiz':
            # show_question will stop the old timer and start a new one with the new widgets
            self.show_question(preserve_vars=True)
        elif self.mode == 'review':
            # review_question will stop the timer (if it was somehow running)
            self.review_question(self.review_index)
        elif self.mode == 'score':
            # show_score will stop the timer (if it was somehow running)
            self.show_score()

    def save_current_checkbox_states(self):
        if self.vars:
            self.saved_vars = [var.get() for var in self.vars]
        else:
            self.saved_vars = []

    def add_dark_mode_button(self):
        # Destroy existing button if it exists
        if self.dark_mode_button and self.dark_mode_button.winfo_exists():
            self.dark_mode_button.destroy()
            self.dark_mode_button = None  # Clear the reference

        # Only create the button if NOT in menu mode
        if self.mode != 'menu':
            btn_text = "🌙" if not self.dark_mode else "☀️"
            self.dark_mode_button = ttk.Button(self.root, text=btn_text, command=self.toggle_theme, style="TButton",
                                               takefocus=0, state='normal')
            self.dark_mode_button.place(relx=1.0, rely=0.0, anchor="ne", x=-10, y=10)

    def main_menu(self):
        self.mode = 'menu'
        self.stop_elapsed_timer()  # Stop timer when returning to menu
        for widget in self.root.winfo_children():
            widget.destroy()

        # Dark mode button is not added in main_menu

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
        self.start_btn = ttk.Button(main_frame, text="🚀 Start Quiz", command=self.start_quiz, state=state,
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

        self.root.geometry(DEFAULT_QUIZ_SIZE)
        self.center_window()
        num_to_sample = min(num, len(self.questions))
        self.quiz_questions = random.sample(self.questions, num_to_sample)

        for q in self.quiz_questions:
            if not q.options:
                q.shuffled_options = []
                q.type = 'CS'
                continue

            correct_opts = [opt for opt in q.options if opt[1]]
            incorrect_opts = [opt for opt in q.options if not opt[1]]

            q.type = 'CS' if correct_opts and random.choice([True, False]) else 'CM'
            if not correct_opts:
                q.type = 'CM'

            if q.type == 'CS':
                if correct_opts:
                    chosen_correct = random.choice(correct_opts)
                    num_incorrect_needed = 4
                    num_incorrect_to_sample = min(num_incorrect_needed, len(incorrect_opts))
                    sampled_incorrect = random.sample(incorrect_opts, num_incorrect_to_sample)
                    q.shuffled_options = [chosen_correct] + sampled_incorrect
                else:
                    q.shuffled_options = random.sample(q.options, min(5, len(q.options)))

                random.shuffle(q.shuffled_options)

            else:  # CM Type
                num_total_options_target = 5
                min_correct_for_cm = min(len(correct_opts), 2) if len(correct_opts) >= 2 else len(correct_opts)
                max_correct_for_cm = min(len(correct_opts), 4)

                if min_correct_for_cm > 0:
                    num_correct_selected = random.randint(min_correct_for_cm, max_correct_for_cm)
                else:
                    num_correct_selected = 0

                chosen_correct = random.sample(correct_opts, num_correct_selected)

                num_incorrect_needed = num_total_options_target - num_correct_selected
                num_incorrect_to_sample = min(num_incorrect_needed, len(incorrect_opts))
                sampled_incorrect = random.sample(incorrect_opts, num_incorrect_to_sample)

                q.shuffled_options = chosen_correct + sampled_incorrect

                if len(q.shuffled_options) < num_total_options_target and len(incorrect_opts) > num_incorrect_to_sample:
                    remaining_slots = num_total_options_target - len(q.shuffled_options)
                    additional_incorrect = random.sample(
                        [opt for opt in incorrect_opts if opt not in sampled_incorrect],
                        min(remaining_slots, len(incorrect_opts) - num_incorrect_to_sample))
                    q.shuffled_options.extend(additional_incorrect)

                random.shuffle(q.shuffled_options)

                if not q.shuffled_options and q.options:
                    q.shuffled_options = random.sample(q.options, min(num_total_options_target, len(q.options)))

        self.current_question_index = 0
        self.user_answers = [[] for _ in self.quiz_questions]
        self.score = 0
        self.max_score = len(self.quiz_questions) * 5 if self.quiz_questions else 0
        self.scores_breakdown = [0] * len(self.quiz_questions)
        self.saved_vars = []
        self.elapsed_seconds = 0

        self.show_question()  # show_question will handle starting the timer

    def show_question(self, preserve_vars=False):
        self.mode = 'quiz'
        self.stop_elapsed_timer()  # Stop existing timer before clearing screen
        for widget in self.root.winfo_children():
            widget.destroy()

        self.add_dark_mode_button()  # Add the enabled button here

        if not (0 <= self.current_question_index < len(self.quiz_questions)):
            self.stop_elapsed_timer()  # Ensure timer is stopped if end reached
            self.calculate_score()
            self.show_score()
            return

        # Create the timer label FIRST
        self.timer_label = ttk.Label(self.root, text="", font=FONT_BUTTON)
        self.timer_label.pack(pady=10)

        # Start the timer loop AFTER the label is created
        self.start_elapsed_timer()

        q = self.quiz_questions[self.current_question_index]
        question_label_wraplength = max(300, self.root.winfo_width() - 40)
        ttk.Label(self.root, text=f"({q.type}) {q.text}",
                  wraplength=question_label_wraplength, justify="left",
                  font=FONT_QUESTION).pack(
            pady=20, anchor='w', padx=20)

        options_frame = ttk.Frame(self.root)
        options_frame.pack(fill='both', expand=True, padx=20, pady=10)

        self.vars = []

        if not q.shuffled_options:
            ttk.Label(options_frame, text="No options available for this question.", font=FONT_OPTION).pack(anchor='w',
                                                                                                            padx=40,
                                                                                                            pady=4)
        else:
            for i, (opt_text, _) in enumerate(q.shuffled_options):
                var = tk.IntVar(value=0)
                cb = ttk.Checkbutton(options_frame, text=opt_text, variable=var, style="Quiz.TCheckbutton")
                cb.pack(anchor='w', padx=40, pady=4)
                self.vars.append(var)

        if preserve_vars:
            if self.current_question_index < len(self.user_answers) and self.user_answers[self.current_question_index]:
                current_answers = self.user_answers[self.current_question_index]
                for i, var_value in enumerate(current_answers):
                    if i < len(self.vars):
                        self.vars[i].set(var_value)
            elif self.saved_vars:
                for i, var_value in enumerate(self.saved_vars):
                    if i < len(self.vars):
                        self.vars[i].set(var_value)
            self.saved_vars = []

        nav_frame = ttk.Frame(self.root)
        nav_frame.pack(side='bottom', fill='x', padx=20, pady=20)
        nav_frame.columnconfigure(0, weight=1)
        nav_frame.columnconfigure(1, weight=0)  # Previous
        # nav_frame.columnconfigure(2, weight=0) # Home
        nav_frame.columnconfigure(3, weight=0)  # Next
        nav_frame.columnconfigure(4, weight=1)

        # home_btn = ttk.Button(nav_frame, text="🏠 Home", command=self.back_to_menu, style="TButton", takefocus=0)
        # home_btn.grid(row=0, column=2, padx=10)

        next_btn = ttk.Button(nav_frame, text="Next ➡️", command=self.next_question, style="TButton", takefocus=0)
        next_btn.grid(row=0, column=3, padx=10)

        if self.current_question_index > 0:
            prev_btn = ttk.Button(nav_frame, text="⬅️ Previous", command=self.prev_question, style="TButton",
                                  takefocus=0)
            prev_btn.grid(row=0, column=1, padx=10)

    def next_question(self):
        while len(self.user_answers) <= self.current_question_index:
            self.user_answers.append([])

        self.user_answers[self.current_question_index] = [var.get() for var in self.vars]
        self.saved_vars = []

        self.current_question_index += 1
        if self.current_question_index >= len(self.quiz_questions):
            # next_question implicitly calls show_score which stops the timer
            self.stop_elapsed_timer()  # Stop timer when quiz ends
            self.calculate_score()
            self.show_score()
        else:
            self.show_question(preserve_vars=True)  # show_question restarts the timer

    def prev_question(self):
        while len(self.user_answers) <= self.current_question_index:
            self.user_answers.append([])

        self.user_answers[self.current_question_index] = [var.get() for var in self.vars]
        self.saved_vars = []

        if self.current_question_index > 0:
            self.current_question_index -= 1
            self.show_question(preserve_vars=True)  # show_question stops and restarts the timer

    def calculate_score(self):
        self.score = 0

        for q_index, q in enumerate(self.quiz_questions):
            # # # Handle questions with no options - they score 0
            # if not q.shuffled_options:
            #     self.scores_breakdown[q_index] = 0  # Explicitly set breakdown score
            #     continue

            # Re-create the correctness map from original options based on shuffled text
            # This mapping is necessary because options are shuffled, but scoring depends on original correctness
            correctness_map = {text: correct for (text, correct) in q.options}

            # Get correctness flags for the options in the *shuffled* order
            correct_flags = [correctness_map.get(opt_text, False) for (opt_text, _) in q.shuffled_options]
            num_options = len(correct_flags)  # Number of options presented in the quiz

            # Get user answers for this specific question index, ensure it matches the number of options
            user_flags_for_q = []
            if q_index < len(self.user_answers) and self.user_answers[q_index]:
                user_flags_for_q = self.user_answers[q_index][:]  # Get a copy
                # Pad or truncate user answers to match the number of options presented for this question
                while len(user_flags_for_q) < num_options:
                    user_flags_for_q.append(0)  # Pad with 0 (not selected)
                user_flags_for_q = user_flags_for_q[:num_options]  # Truncate if somehow too long
            else:
                # If no answer recorded for this question, treat as all not selected
                user_flags_for_q = [0] * num_options

            q_score = 0  # Initialize score for this question

            # Find indices of user selected options in the SHUFFLED list
            user_selected_shuffled_indices = [i for i, is_selected in enumerate(user_flags_for_q) if is_selected]

            # Find indices of correct options in the SHUFFLED list based on original correctness
            correct_shuffled_indices = [i for i, (opt_text, _) in enumerate(q.shuffled_options) if
                                        correctness_map.get(opt_text, False)]

            if q.type == 'CS':  # Single Correct (Simplified Logic)
                # Score 5 points if and only if exactly one option was selected AND that option is one of the correct ones.
                if len(user_selected_shuffled_indices) == 1 and \
                        user_selected_shuffled_indices[0] in correct_shuffled_indices:
                    q_score = 5
            else:  # CM
                if len(user_selected_shuffled_indices) < 2 or len(user_selected_shuffled_indices) > 4:
                    q_score = 0
                else:
                    q_score = 5
                    for i in range(num_options):
                        if (user_flags_for_q[i] and not correct_flags[i]) or (not user_flags_for_q[i] and correct_flags[i]):
                            q_score -= 1
                    # Apply minimum of 0 and maximum of 5 points for this question
                    q_score = max(0, q_score)
                    q_score = min(q_score, 5)
            # Store the calculated score for this question in the breakdown
            self.scores_breakdown[q_index] = q_score
            # Add this question's score to the total score
            self.score += q_score

    def show_score(self):
        self.mode = 'score'
        self.stop_elapsed_timer()  # Stop timer when showing score
        for widget in self.root.winfo_children():
            widget.destroy()

        self.add_dark_mode_button()  # Add the enabled button here

        ttk.Label(self.root, text="🏆 Quiz Complete! 🏆", font=FONT_QUESTION).pack(pady=20)

        actual_max_score = len(self.quiz_questions) * 5 if self.quiz_questions else 0
        ttk.Label(self.root, text=f"Total Score: {self.score} / {actual_max_score} points",
                  font=(FONT_FAMILY, 20, "bold")).pack(pady=5)
        ttk.Label(self.root, text=f"Final grade: {(self.score / actual_max_score) * 9 + 1} / {10}",
                  font=(FONT_FAMILY, 20, "bold")).pack(pady=5)

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

    def review_question(self, index):
        self.mode = 'review'
        self.stop_elapsed_timer()  # Stop timer when showing review
        self.review_index = index

        for widget in self.root.winfo_children():
            widget.destroy()

        self.add_dark_mode_button()  # Add the enabled button here

        if not (0 <= index < len(self.quiz_questions)):
            self.show_score()
            return

        q = self.quiz_questions[index]

        num_options = len(q.shuffled_options) if q.shuffled_options else 0
        user_ans_for_q = []
        if index < len(self.user_answers) and self.user_answers[index]:
            user_ans_for_q = self.user_answers[index][:]
            while len(user_ans_for_q) < num_options:
                user_ans_for_q.append(0)
            user_ans_for_q = user_ans_for_q[:num_options]
        else:
            user_ans_for_q = [0] * num_options

        question_label_wraplength = max(300, self.root.winfo_width() - 40)
        ttk.Label(self.root, text=f"({q.type}): {q.text}", wraplength=question_label_wraplength, justify="left",
                  font=FONT_QUESTION).pack(pady=20, anchor='w', padx=20)

        legend_frame = ttk.Frame(self.root)
        legend_frame.pack(pady=(0, 10), padx=20, anchor='w', fill='x')

        label_bg_color = self.root.cget('bg')
        default_review_fg_color = self.default_fg_color

        def create_legend_label(parent, text_symbol, specific_fg_color):
            lbl = tk.Label(parent, text=text_symbol, font=FONT_SMALL, fg=specific_fg_color, bg=label_bg_color)
            lbl.pack(side='left', padx=6)

        create_legend_label(legend_frame, "✅ Correct", "green")
        create_legend_label(legend_frame, "❌ Wrong", "red")
        create_legend_label(legend_frame, "🟠 Missed", "orange")

        content_frame = ttk.Frame(self.root)
        content_frame.pack(fill='both', expand=True, padx=20, pady=10)

        content_bg_color = self.root.cget('bg')

        if not q.shuffled_options:
            tk.Label(content_frame, text="No options were available for this question.", font=FONT_OPTION,
                     bg=content_bg_color, fg=default_review_fg_color).pack(anchor='w', padx=40, pady=2)
        else:
            correctness_map = {text: correct for (text, correct) in q.options}

            for i, (opt_text, _) in enumerate(q.shuffled_options):
                correct = correctness_map.get(opt_text, False)

                selected = user_ans_for_q[i] if i < len(user_ans_for_q) else 0
                mark = ""
                text_color_for_option = default_review_fg_color

                if correct and selected:
                    mark = "✅"
                    text_color_for_option = "green"
                elif not correct and selected:
                    mark = "❌"
                    text_color_for_option = "red"
                elif correct and not selected:
                    mark = "🟠"
                    text_color_for_option = "orange"
                elif not correct and not selected:
                    mark = ""

                full_text = f"{mark} {opt_text}"
                lbl = tk.Label(content_frame, text=full_text, font=FONT_OPTION, fg=text_color_for_option,
                               bg=content_bg_color,
                               anchor='w', justify='left')
                lbl.pack(anchor='w', padx=40, pady=2)

        q_score_breakdown = self.scores_breakdown[index]
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
            prev_btn = ttk.Button(nav_frame, text="⬅️ Previous", command=lambda: self.review_question(index - 1),
                                  style="TButton", takefocus=0)
            prev_btn.grid(row=0, column=1, padx=10, sticky='e')

        score_btn = ttk.Button(nav_frame, text="Back to Score", command=self.show_score, style="TButton", takefocus=0)
        score_btn.grid(row=0, column=2, padx=10, sticky='nsew')

        if index < len(self.quiz_questions) - 1:
            next_btn = ttk.Button(nav_frame, text="Next ➡️", command=lambda: self.review_question(index + 1),
                                  style="TButton", takefocus=0)
            next_btn.grid(row=0, column=3, padx=10, sticky='w')

    def start_another_quiz(self):
        # stop_elapsed_timer is called in show_score before this method
        self.elapsed_seconds = 0  # Reset timer for the new quiz
        self.user_answers = []
        self.score = 0
        self.scores_breakdown = []
        self.current_question_index = 0
        self.review_index = 0
        self.saved_vars = []
        self.start_quiz()  # start_quiz calls show_question which starts the timer

    def back_to_menu(self):
        self.stop_elapsed_timer()  # Stop timer when going back to menu
        self.elapsed_seconds = 0  # Reset timer for consistency, though not displayed in menu
        self.root.geometry(DEFAULT_MENU_SIZE)
        self.center_window()
        self.quiz_questions = []
        self.user_answers = []
        self.score = 0
        self.max_score = 0
        self.scores_breakdown = []
        self.current_question_index = 0
        self.review_index = 0
        self.saved_vars = []
        self.main_menu()  # main_menu does not start the timer

    # start_elapsed_timer is now called ONLY from show_question (after creating the label)
    def start_elapsed_timer(self):
        # Ensure the label exists before starting the timer loop that updates it
        if not hasattr(self, 'timer_label') or not self.timer_label or not self.timer_label.winfo_exists():
            print("Warning: Attempted to start timer without a valid timer_label.")
            return  # Don't start timer if label isn't ready

        self.timer_running = True
        if self.timer_id is not None:
            self.root.after_cancel(self.timer_id)
            self.timer_id = None

        self._display_elapsed_time()  # Initial display
        self.timer_id = self.root.after(1000, self._timer_tick)  # Schedule the first tick

    def _timer_tick(self):
        if not self.timer_running:
            self.timer_id = None  # Clear ID when stopping
            return

        self.elapsed_seconds += 1
        self._display_elapsed_time()

        # Only reschedule if timer is still running (prevents scheduling after stop is called)
        if self.timer_running:
            self.timer_id = self.root.after(1000, self._timer_tick)
        else:
            self.timer_id = None

    def _display_elapsed_time(self):
        if not hasattr(self, 'timer_label') or not self.timer_label or not self.timer_label.winfo_exists():
            return

        hours, remainder = divmod(self.elapsed_seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        time_parts = []
        if hours > 0: time_parts.append(f"{hours}h")
        if minutes > 0 or hours > 0: time_parts.append(f"{minutes}m")
        time_parts.append(f"{seconds}s")

        time_str = " ".join(time_parts) if time_parts else "0s"
        display_text = f"⏱️ Time elapsed: {time_str}"
        try:
            self.timer_label.config(text=display_text)
        except tk.TclError as e:
            # Catch potential TclError if widget is destroyed between check and config
            print(f"Error updating timer label: {e}")
            self.stop_elapsed_timer()  # Stop timer if update fails

    # stop_elapsed_timer is now called explicitly before clearing screens
    def stop_elapsed_timer(self):
        self.timer_running = False
        if self.timer_id is not None:
            self.root.after_cancel(self.timer_id)
            self.timer_id = None


if __name__ == "__main__":
    root = tk.Tk()
    app = QuizApp(root)
    root.mainloop()
