# --------------------------------------------------------------------------------
# Copyright (c) 2025 Capatina Nicolae
# All rights reserved.
#
# This software, Quiz App ("the Software"), is licensed, not sold.
# The Software is provided "as is", without warranty of any kind, express or
# implied, including but not limited to the warranties of merchantability,
# fitness for a particular purpose and noninfringement. In no event shall the
# authors or copyright holders be liable for any claim, damages or other
# liability, whether in an action of contract, tort or otherwise, arising from,
# out of or in connection with the
# Software or the use or other dealings in the
# Software.
#
# LICENSE TERMS:
#
# 1.  GRANT OF LICENSE: The copyright holder grants you a personal, non-exclusive,
#     non-transferable, royalty-free license to use, copy, and modify the
#     Software for personal, non-commercial purposes only.
#
# 2.  NON-COMMERCIAL USE: You may not use the Software for any commercial
#     purposes. Commercial purposes include, but are not limited to, selling the
#     Software, using the Software as part of a product or service that is sold,
#     or using the Software to generate revenue directly or indirectly.
#
# 3.  REDISTRIBUTION: You may redistribute the Software in its original or modified
#     form provided that:
#     a.  This copyright notice and license terms are included with all copies or
#         substantial portions of the Software.
#     b.  If you modify the Software, you must clearly indicate that it has been
#         modified.
#     c.  You do not charge a fee for the Software itself, though you may charge
#         for media or services associated with distributing it, as long as this
#         is not for commercial gain from the Software itself.
#
# 4.  NO ENDORSEMENT: This license does not grant you any rights to use the
#     names, logos, or trademarks of the copyright holder without prior written
#     permission.
#
# By using, copying, or modifying the Software, you agree to be bound by the
# terms of this license. If you do not agree to the terms of this license, do
# not use, copy, or modify the Software.
# --------------------------------------------------------------------------------

import ui
import dialogs
import random
import re
import time
import json
import datetime


class Question:
    def __init__(self, q_number, text, options):
        self.q_number = q_number
        self.text = text
        self.options = options
        self.shuffled_options = []
        self.type = None


def parse_questions_from_file(file_path):
    """
    Parses a text file with multiple-choice questions and returns a list of Question objects.

    The function is designed to handle blocks of questions separated by blank lines.
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except FileNotFoundError:
        print(f"Error: The file '{file_path}' was not found.")
        return []

    questions = []
    blocks = re.findall(r'(?s)(?m)^(?:\\s*)?(\d+)\.\s*(.*?)(?=\n(?:\\s*)?\d+\.\s*|\Z)', content.strip())

    for q_number_str, block_content in blocks:
        q_number = int(q_number_str)
        lines = block_content.strip().split('\n')
        question_text = lines[0].strip()
        options = []

        for line in lines[1:]:
            line = line.strip()
            if not line:
                continue

            match = re.match(r'^[a-j]\.\s+(?:\\s*)?\[(y|x)\]\s+(.*)', line)

            if match:
                correctness, text = match.groups()
                options.append((text.strip(), correctness == 'y'))

        if question_text and options:
            questions.append(Question(q_number, question_text, options))

    return questions


class QuizApp:
    def __init__(self):
        self.main_view = ui.View()
        self.main_view.name = "Quiz App"
        self.main_view.frame = (0, 0, 600, 800)
        self.questions = []
        self.quiz_questions = []
        self.current_question_index = 0
        self.user_answers = []
        self.score = 0
        self.scores_breakdown = []
        self.num_questions = 5
        self.start_time = 0
        self.is_presented = False
        # Added quiz file name
        self.quiz_file_name = "N/A"

        self.user_name_for_copyright = "Capatina Nicolae"
        self.current_year_for_copyright = time.strftime("%Y")
        self.copyright_text_string = f"© {self.current_year_for_copyright} {self.user_name_for_copyright}"

        self.themes = {
            'light': {
                'bg': 'white', 'text': 'black', 'button_bg': '#007AFF', 'button_text': 'white',
                'textfield_bg': '#EFEFF4', 'textfield_text': 'black', 'switch_tint': '#34C759',
                'progress_text': '#555555', 'correct_text': 'green',
                'correct_not_selected_text': '#0066CC', 'incorrect_selected_text': 'red',
                'incorrect_not_selected_text': 'dimgray',
                'copyright_text_color': '#A0A0A0'
            },
            'dark': {
                'bg': '#1C1C1E', 'text': '#EBEBF5', 'button_bg': '#0A84FF', 'button_text': 'white',
                'textfield_bg': '#2C2C2E', 'textfield_text': 'white', 'switch_tint': '#30D158',
                'progress_text': '#999999', 'correct_text': '#32D74B',
                'correct_not_selected_text': '#5AC8FA', 'incorrect_selected_text': '#FF453A',
                'incorrect_not_selected_text': '#8E8E93',
                'copyright_text_color': '#606060'
            }
        }
        self.dark_mode_enabled = False
        self.load_settings()
        self.current_theme = self.themes['dark'] if self.dark_mode_enabled else self.themes['light']

        self.main_menu()

    def _get_wrapped_text_height(self, text, width, font_name, font_size):
        """Calculates the height of a text string when wrapped to a given width."""
        temp_label = ui.Label(text=text, font=(font_name, font_size), number_of_lines=0)
        temp_label.width = width
        temp_label.size_to_fit()
        return temp_label.height

    def _add_copyright_label(self):
        copyright_label = ui.Label(text=self.copyright_text_string)
        copyright_label.font = ('Helvetica', 9)
        copyright_label.text_color = self.get_theme_color('copyright_text_color', self.get_theme_color('progress_text'))
        copyright_label.alignment = ui.ALIGN_RIGHT
        text_width, text_height = ui.measure_string(
            copyright_label.text, font=copyright_label.font, alignment=copyright_label.alignment
        )
        margin = 5
        label_width = text_width + 10
        label_height = text_height + 4
        copyright_label.frame = (
            self.main_view.width - label_width - margin,
            self.main_view.height - label_height - margin,
            label_width, label_height
        )
        copyright_label.flex = 'RB'
        self.main_view.add_subview(copyright_label)

    def load_settings(self):
        try:
            with open('quiz_settings.json', 'r') as f:
                settings = json.load(f)
                self.dark_mode_enabled = settings.get('dark_mode_enabled', False)
        except (FileNotFoundError, json.JSONDecodeError, Exception):
            self.dark_mode_enabled = False

    def save_settings(self):
        settings = {'dark_mode_enabled': self.dark_mode_enabled}
        try:
            with open('quiz_settings.json', 'w') as f:
                json.dump(settings, f)
        except IOError:
            print("Error: Could not save theme settings.")

    def save_results(self, score, total_possible, grade, duration, quiz_file_name, num_questions_attempted, timestamp):
        results_data = []
        try:
            with open('results.cfg', 'r') as f:
                results_data = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            # File doesn't exist or is empty/corrupt, start with an empty list
            results_data = []

        new_result = {
            'timestamp': timestamp,
            'quiz_file': quiz_file_name,
            'score': score,
            'total_possible': total_possible,
            'grade': grade,
            'duration_seconds': duration,
            'num_questions_attempted': num_questions_attempted,
            'questions_breakdown': []
        }

        # Add details for each question attempted
        for i, (q, user_res) in enumerate(self.user_answers):
            correct_res = [is_c for _, is_c in q.shuffled_options]
            question_info = {
                'original_q_number': q.q_number,
                'question_text': q.text,
                'type': q.type,
                'shuffled_options': [(opt_text, is_c) for opt_text, is_c in q.shuffled_options],
                'user_selection': user_res,
                'correct_answers': correct_res,
                'score_for_this_question': self.scores_breakdown[i]
            }
            new_result['questions_breakdown'].append(question_info)

        results_data.append(new_result)

        try:
            with open('results.cfg', 'w') as f:
                json.dump(results_data, f, indent=4)
        except IOError:
            print("Error: Could not save quiz results.")

    def get_theme_color(self, key, default='black'):
        return self.current_theme.get(key, default)

    def clear_view(self):
        for subview in list(self.main_view.subviews):
            self.main_view.remove_subview(subview)

    def format_time(self, seconds):
        if seconds < 60: return f"{seconds} seconds"
        minutes, remaining_seconds = divmod(seconds, 60)
        if remaining_seconds == 0: return f"{minutes} minute{'s' if minutes != 1 else ''}"
        return f"{minutes}m {remaining_seconds}s"

    def calculate_grade(self, score, total):
        if total == 0: return "N/A"
        grade = (score / total) * 9 + 1
        return f"{grade:.2f}"

    def toggle_dark_mode(self, sender):
        self.dark_mode_enabled = sender.value
        self.current_theme = self.themes['dark'] if self.dark_mode_enabled else self.themes['light']
        self.save_settings()
        self.main_menu()

    def main_menu(self):
        self.main_view.background_color = self.get_theme_color('bg')
        self.clear_view()
        self.main_view.flex = 'WH'

        title_label = ui.Label(text='Quiz App', font=('Helvetica-Bold', 32), alignment=ui.ALIGN_CENTER)
        title_label.text_color = self.get_theme_color('text')
        title_label.frame = (0, 60, self.main_view.width, 50)
        title_label.flex = 'W'
        self.main_view.add_subview(title_label)

        load_btn = ui.Button(title='Load Quiz File', font=('Helvetica', 18))
        load_btn.background_color = self.get_theme_color('button_bg')
        load_btn.tint_color = self.get_theme_color('button_text')
        load_btn.corner_radius = 8
        load_btn.frame = (80, 150, self.main_view.width - 160, 50)
        load_btn.flex = 'W'
        load_btn.action = self.load_file
        self.main_view.add_subview(load_btn)

        num_q_label = ui.Label(text='Number of questions:', alignment=ui.ALIGN_CENTER, font=('Helvetica', 16))
        num_q_label.text_color = self.get_theme_color('text')
        num_q_label.frame = (0, 230, self.main_view.width, 40)
        num_q_label.flex = 'W'
        self.main_view.add_subview(num_q_label)

        self.num_field = ui.TextField(text='5', alignment=ui.ALIGN_CENTER, keyboard_type=ui.KEYBOARD_NUMBER_PAD,
                                      font=('Helvetica', 18))
        self.num_field.background_color = self.get_theme_color('textfield_bg')
        self.num_field.text_color = self.get_theme_color('textfield_text')
        self.num_field.tint_color = self.get_theme_color('text')
        self.num_field.bordered = False
        self.num_field.corner_radius = 5
        self.num_field.frame = (self.main_view.width / 2 - 60, 280, 120, 40)
        self.num_field.flex = 'LR'
        self.main_view.add_subview(self.num_field)

        start_btn = ui.Button(title='Start Quiz', font=('Helvetica', 18))
        start_btn.background_color = self.get_theme_color('button_bg')
        start_btn.tint_color = self.get_theme_color('button_text')
        start_btn.corner_radius = 8
        start_btn.frame = (80, 360, self.main_view.width - 160, 50)
        start_btn.flex = 'W'
        start_btn.action = self.start_quiz
        self.main_view.add_subview(start_btn)

        dark_mode_y_pos = 430
        dark_mode_label = ui.Label(text='Dark Mode:', font=('Helvetica', 16))
        dark_mode_label.text_color = self.get_theme_color('text')
        dark_mode_label.frame = (80, dark_mode_y_pos, 150, 40)
        dark_mode_label.flex = 'W'
        self.main_view.add_subview(dark_mode_label)

        self.dark_mode_switch = ui.Switch(value=self.dark_mode_enabled)
        self.dark_mode_switch.frame = (self.main_view.width - 80 - 80, dark_mode_y_pos + 4, 80, 32)
        self.dark_mode_switch.flex = 'L'
        self.dark_mode_switch.tint_color = self.get_theme_color('switch_tint')
        self.dark_mode_switch.action = self.toggle_dark_mode
        self.main_view.add_subview(self.dark_mode_switch)

        self._add_copyright_label()

        if not self.is_presented:
            self.main_view.present('fullscreen')
            self.is_presented = True

    def load_file(self, sender):
        try:
            file_path = dialogs.pick_document(types=['public.text'])
            if file_path:
                self.questions = parse_questions_from_file(file_path)
                # Store the file name
                self.quiz_file_name = file_path.split('/')[-1]
                dialogs.alert('Loaded', f'{len(self.questions)} questions loaded from {self.quiz_file_name}.',
                              button1='OK')
        except Exception as e:
            dialogs.alert('Error', f'Failed to load or parse the file.\n\n{e}', button1='OK')

    def start_quiz(self, sender):
        try:
            num = int(self.num_field.text)
        except ValueError:
            num = 5
        self.num_questions = min(num, len(self.questions))

        if len(self.questions) == 0:
            dialogs.alert("No Questions", "Please load a quiz file first.", button1='OK')
            return
        if self.num_questions == 0:
            dialogs.alert("Info", "Number of questions is 0. No quiz will start.", button1='OK')
            return

        self.quiz_questions = []
        # Initial filter for questions that are viable candidates (have at least 5 options and one correct answer)
        available_questions = [q for q in self.questions if
                               len(q.options) >= 5 and sum(1 for opt, is_c in q.options if is_c) > 0]

        if len(available_questions) < self.num_questions:
            actual_num = len(available_questions)
            if actual_num == 0:
                dialogs.alert("Quiz Error", "No valid questions found. Check file.", button1='OK')
                return
            dialogs.alert("Quiz Info", f"Not enough valid questions for {self.num_questions}. Using {actual_num}.",
                          button1='OK')
            self.num_questions = actual_num

        temp_questions_to_process = random.sample(available_questions, self.num_questions)
        for q_original in temp_questions_to_process:
            q = q_original
            correct_options = [opt for opt in q.options if opt[1]]
            incorrect_options = [opt for opt in q.options if not opt[1]]
            current_q_shuffled_options = []

            # --- MODIFIED LOGIC ---
            # If the source question has exactly 5 options, treat it as a mandatory CS (single-choice) question.
            if len(q.options) == 5:
                # It's only valid if it has exactly one correct answer.
                if len(correct_options) == 1:
                    q.type = 'CS'
                    current_q_shuffled_options = list(q.options)  # Use the existing 5 options
                else:
                    # If a 5-option question doesn't have exactly 1 correct answer, it's invalid for this mode.
                    continue
            # If the source question has MORE than 5 options, use the original logic to create a 5-option quiz question.
            else:
                q.type = random.choice(['CS', 'CM'])
                if q.type == 'CS':
                    if correct_options and len(incorrect_options) >= 4:
                        current_q_shuffled_options = random.sample(correct_options, 1) + random.sample(
                            incorrect_options, 4)
                    else:
                        continue  # Not enough options to build a CS question
                else:  # q.type == 'CM'
                    min_correct_cm = 2
                    max_correct_cm = min(4, len(correct_options))
                    if max_correct_cm < min_correct_cm: continue
                    n_correct = random.randint(min_correct_cm, max_correct_cm)
                    n_incorrect = 5 - n_correct
                    if len(incorrect_options) < n_incorrect: continue
                    current_q_shuffled_options = random.sample(correct_options, n_correct) + random.sample(
                        incorrect_options, n_incorrect)

            if not current_q_shuffled_options or len(current_q_shuffled_options) != 5: continue

            random.shuffle(current_q_shuffled_options)
            q.shuffled_options = current_q_shuffled_options
            self.quiz_questions.append(q)

        if not self.quiz_questions:
            dialogs.alert("Quiz Error", "Failed to prepare questions. Check that questions have enough options.",
                          button1='OK')
            return

        self.current_question_index = 0
        self.user_answers = []
        self.score = 0
        self.scores_breakdown = []
        self.start_time = time.time()
        self.show_question()

    def show_question(self):
        self.main_view.background_color = self.get_theme_color('bg')
        self.clear_view()

        if self.current_question_index >= len(self.quiz_questions):
            self.show_score()
            return

        q = self.quiz_questions[self.current_question_index]

        progress_text = (f"Question {self.current_question_index + 1} of {len(self.quiz_questions)} "
                         f"(Original #{q.q_number})")
        progress_label = ui.Label(text=progress_text, font=('Helvetica', 14), alignment=ui.ALIGN_CENTER)
        progress_label.text_color = self.get_theme_color('progress_text')
        progress_label.frame = (0, 20, self.main_view.width, 30)
        progress_label.flex = 'W'
        self.main_view.add_subview(progress_label)

        q_label_width = self.main_view.width - 40
        q_text_with_type = f"{q.type}: {q.text}"
        q_label_height = self._get_wrapped_text_height(q_text_with_type, q_label_width, 'Helvetica', 16)

        q_label = ui.Label(text=q_text_with_type, number_of_lines=0, font=('Helvetica', 16))
        q_label.text_color = self.get_theme_color('text')
        q_label.frame = (20, 60, q_label_width, q_label_height)
        q_label.flex = 'W'
        self.main_view.add_subview(q_label)

        self.vars = []
        y_pos = q_label.y + q_label.height + 20
        opt_v_margin = 15

        for opt_text, _ in q.shuffled_options:
            lbl_width = self.main_view.width - 130
            lbl_height = self._get_wrapped_text_height(opt_text, lbl_width, 'Helvetica', 14)

            row_height = max(40, lbl_height)

            sw = ui.Switch()
            sw.frame = (30, y_pos + (row_height / 2) - (sw.height / 2), 60, 40)
            sw.tint_color = self.get_theme_color('switch_tint')
            self.main_view.add_subview(sw)

            lbl = ui.Label(text=opt_text, number_of_lines=0, font=('Helvetica', 14))
            lbl.text_color = self.get_theme_color('text')
            lbl.frame = (100, y_pos + (row_height / 2) - (lbl_height / 2), lbl_width, lbl_height)
            lbl.flex = 'W'
            self.main_view.add_subview(lbl)

            self.vars.append(sw)
            y_pos += row_height + opt_v_margin

        next_btn = ui.Button(title='Next', font=('Helvetica', 18))
        next_btn.background_color = self.get_theme_color('button_bg')
        next_btn.tint_color = self.get_theme_color('button_text')
        next_btn.corner_radius = 8
        next_btn.frame = (80, y_pos, self.main_view.width - 160, 50)
        next_btn.flex = 'W'
        next_btn.action = self.next_question
        self.main_view.add_subview(next_btn)

        self._add_copyright_label()

    def next_question(self, sender):
        """
        RESTORED: This method handles scoring for both CS and CM questions.
        """
        q = self.quiz_questions[self.current_question_index]
        user_res = [var.value for var in self.vars]
        correct_res = [is_c for _, is_c in q.shuffled_options]
        self.user_answers.append((q, user_res))
        q_score = 0
        if q.type == 'CS':
            if sum(user_res) == 1 and user_res == correct_res: q_score = 5
        elif q.type == 'CM':
            selected_count = sum(user_res)
            num_correct_opts = sum(1 for _, is_c in q.shuffled_options if is_c)
            if 2 <= selected_count <= 4:
                q_score = 5
                for u, c in zip(user_res, correct_res):
                    if u != c: q_score -= 1
                q_score = max(0, q_score)
        self.score += q_score
        self.scores_breakdown.append(q_score)
        self.current_question_index += 1
        if self.current_question_index >= len(self.quiz_questions):
            self.show_score()
        else:
            self.show_question()

    def show_score(self):
        self.main_view.background_color = self.get_theme_color('bg')
        self.clear_view()
        duration = int(time.time() - self.start_time)
        total_possible = len(self.quiz_questions) * 5 if self.quiz_questions else 0
        grade = self.calculate_grade(self.score, total_possible)
        time_str = self.format_time(duration)
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Save results before displaying the score
        self.save_results(self.score, total_possible, grade, duration,
                          self.quiz_file_name, len(self.quiz_questions), timestamp)

        summary = (f'Quiz Completed!\nScore: {self.score}/{total_possible}\nGrade: {grade}\n'
                   f'Time: {time_str}\nDate: {timestamp.split(" ")[0]}\nFile: {self.quiz_file_name}')
        score_lbl = ui.Label(text=summary, number_of_lines=0, alignment=ui.ALIGN_CENTER, font=('Helvetica', 20))
        score_lbl.text_color = self.get_theme_color('text')
        score_lbl.frame = (20, 150, self.main_view.width - 40, 200) # Increased height to fit new info
        score_lbl.flex = 'W'
        self.main_view.add_subview(score_lbl)

        review_btn = ui.Button(title='Review Answers', font=('Helvetica', 18))
        review_btn.background_color = self.get_theme_color('button_bg')
        review_btn.tint_color = self.get_theme_color('button_text')
        review_btn.corner_radius = 8
        review_btn.frame = (80, 380, self.main_view.width - 160, 50) # Adjusted y-position
        review_btn.flex = 'W'
        review_btn.action = self.review_answers
        self.main_view.add_subview(review_btn)

        home_btn = ui.Button(title='Main Menu', font=('Helvetica', 18))
        home_btn.background_color = self.get_theme_color('button_bg')
        home_btn.tint_color = self.get_theme_color('button_text')
        home_btn.corner_radius = 8
        home_btn.frame = (80, 450, self.main_view.width - 160, 50) # Adjusted y-position
        home_btn.flex = 'W'
        home_btn.action = lambda s: self.main_menu()
        self.main_view.add_subview(home_btn)

        self._add_copyright_label()

    def review_answers(self, sender):
        if not self.user_answers: self.main_menu(); return
        self.review_index = 0
        self.show_review()

    def show_review(self):
        self.main_view.background_color = self.get_theme_color('bg')
        self.clear_view()

        if not (0 <= self.review_index < len(self.user_answers)):
            self.main_menu()
            return

        q, user_res = self.user_answers[self.review_index]
        q_score = self.scores_breakdown[self.review_index] if self.review_index < len(self.scores_breakdown) else 'N/A'

        prog_text = (f"Review {self.review_index + 1}/{len(self.user_answers)} "
                     f"(Original #{q.q_number} | Score: {q_score}/5)")
        prog_lbl = ui.Label(text=prog_text, alignment=ui.ALIGN_CENTER, font=('Helvetica', 14))
        prog_lbl.text_color = self.get_theme_color('progress_text')
        prog_lbl.frame = (0, 20, self.main_view.width, 30)
        prog_lbl.flex = 'W'
        self.main_view.add_subview(prog_lbl)

        q_label_width = self.main_view.width - 40
        q_text_with_type = f"{q.type}: {q.text}"
        q_label_height = self._get_wrapped_text_height(q_text_with_type, q_label_width, 'Helvetica', 16)

        q_lbl = ui.Label(text=q_text_with_type, number_of_lines=0, font=('Helvetica', 16))
        q_lbl.text_color = self.get_theme_color('text')
        q_lbl.frame = (20, 60, q_label_width, q_label_height)
        q_lbl.flex = 'W'
        self.main_view.add_subview(q_lbl)

        y_pos = q_lbl.y + q_lbl.height + 20
        opt_v_margin = 15

        for (opt_txt, is_c), sel in zip(q.shuffled_options, user_res):
            color_key = ''
            if is_c and sel:
                color_key = 'correct_text'
            elif is_c and not sel:
                color_key = 'correct_not_selected_text'
            elif not is_c and sel:
                color_key = 'incorrect_selected_text'
            else:
                color_key = 'incorrect_not_selected_text'

            lbl_width = self.main_view.width - 60
            lbl_height = self._get_wrapped_text_height(opt_txt, lbl_width, 'Helvetica', 14)

            lbl = ui.Label(text=opt_txt, number_of_lines=0, font=('Helvetica', 14))
            lbl.text_color = self.get_theme_color(color_key)
            lbl.frame = (30, y_pos, lbl_width, lbl_height)
            lbl.flex = 'W'
            self.main_view.add_subview(lbl)

            y_pos += lbl_height + opt_v_margin

        btn_y = y_pos + 10
        btn_w, btn_h = 100, 50

        # Previous Button
        btn_prev = ui.Button(title='Prev', font=('Helvetica', 16))
        btn_prev.background_color = self.get_theme_color('button_bg')
        btn_prev.tint_color = self.get_theme_color('button_text')
        btn_prev.corner_radius = 8
        btn_prev.frame = (30, btn_y, btn_w, btn_h)
        btn_prev.action = lambda s: self.change_review(-1)
        btn_prev.enabled = self.review_index > 0
        self.main_view.add_subview(btn_prev)

        # Home Button
        btn_home = ui.Button(title='Home', font=('Helvetica', 16))
        btn_home.background_color = self.get_theme_color('button_bg')
        btn_home.tint_color = self.get_theme_color('button_text')
        btn_home.corner_radius = 8
        btn_home.frame = (self.main_view.width / 2 - btn_w / 2, btn_y, btn_w, btn_h)
        btn_home.flex = 'LR'
        btn_home.action = lambda s: self.main_menu()
        self.main_view.add_subview(btn_home)

        # Right-side button: "Next" or "Results"
        right_button = ui.Button(font=('Helvetica', 16))
        right_button.background_color = self.get_theme_color('button_bg')
        right_button.tint_color = self.get_theme_color('button_text')
        right_button.corner_radius = 8
        right_button.frame = (self.main_view.width - btn_w - 30, btn_y, btn_w, btn_h)
        right_button.flex = 'L'

        if self.review_index < len(self.user_answers) - 1:
            right_button.title = 'Next'
            right_button.action = lambda s: self.change_review(1)
        else:
            right_button.title = 'Results'
            # The corrected line:
            right_button.action = lambda s: self.show_score()
        self.main_view.add_subview(right_button)

        self._add_copyright_label()

    def change_review(self, delta):
        new_idx = self.review_index + delta
        if 0 <= new_idx < len(self.user_answers):
            self.review_index = new_idx
            self.show_review()


if __name__ == '_main_':
    app = QuizApp()