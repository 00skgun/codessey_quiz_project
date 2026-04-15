import json


class Quiz:
    def __init__(self, question, choices, answer):
        self.question = question
        self.choices = choices
        self.answer = answer

    def display(self):
        print(self.question)
        for index, choice in enumerate(self.choices, start=1):
            print(f"{index}. {choice}")

    def is_correct(self, user_answer):
        return user_answer == self.answer

    def to_dict(self):
        return {
            "question": self.question,
            "choices": self.choices,
            "answer": self.answer
        }

    @classmethod
    def from_dict(cls, data):
        return cls(
            data["question"],
            data["choices"],
            data["answer"]
        )


class QuizGame:
    def __init__(self):
        self.state_file = "state.json"
        self.quizzes = []
        self.best_score = None
        self.is_running = True
        self.load_state()

    def get_default_quizzes(self):
        return [
            Quiz(
                "야구에서 한 팀이 공격할 때 아웃 3개를 당하면 어떻게 될까?",
                ["경기가 종료된다", "수비를 계속한다", "공수 교대가 된다", "점수가 1점 추가된다"],
                3
            ),
            Quiz(
                "야구에서 홈런은 보통 어떤 상황을 의미할까?",
                ["타자가 친 공이 땅에 한 번 튄 경우", "타자가 친 공이 담장을 넘어간 경우", "투수가 공을 빠르게 던진 경우", "포수가 공을 잡지 못한 경우"],
                2
            ),
            Quiz(
                "야구 경기에서 스트라이크가 3번 선언되면 타자는 어떻게 될까?",
                ["볼넷으로 출루한다", "아웃된다", "2루로 진루한다", "다시 타석에 선다"],
                2
            ),
            Quiz(
                "주자가 1루, 2루, 3루를 모두 돌아 다시 들어오면 무엇이 될까?",
                ["아웃", "볼넷", "1점", "연장전"],
                3
            ),
            Quiz(
                "야구에서 투수가 던진 공이 스트라이크존을 벗어나고 타자가 치지 않으면 무엇이 선언될까?",
                ["파울", "볼", "아웃", "세이프"],
                2
            ),
            Quiz(
                "야구에서 수비수가 친 공을 땅에 닿기 전에 바로 잡으면 타자는 어떻게 될까?",
                ["안타가 된다", "볼넷이 된다", "아웃된다", "2루타가 된다"],
                3
            ),
            Quiz(
                "야구에서 타자가 4개의 볼을 골라내면 무엇이 될까?",
                ["삼진", "볼넷", "홈런", "도루"],
                2
            )
        ]

    def load_state(self):
        try:
            with open(self.state_file, "r", encoding="utf-8") as file:
                data = json.load(file)

            quizzes_data = data.get("quizzes", [])
            self.quizzes = [Quiz.from_dict(item) for item in quizzes_data]
            self.best_score = data.get("best_score")

            if len(self.quizzes) == 0:
                self.quizzes = self.get_default_quizzes()

            print(f"저장된 데이터를 불러왔습니다. 퀴즈 {len(self.quizzes)}개")
        except FileNotFoundError:
            self.quizzes = self.get_default_quizzes()
            self.best_score = None
            print("state.json 파일이 없어 기본 퀴즈로 시작합니다.")
        except (json.JSONDecodeError, KeyError, TypeError):
            self.quizzes = self.get_default_quizzes()
            self.best_score = None
            print("state.json 파일이 손상되어 기본 퀴즈로 복구했습니다.")
            self.save_state()
        except OSError:
            self.quizzes = self.get_default_quizzes()
            self.best_score = None
            print("파일을 읽는 중 오류가 발생해 기본 퀴즈로 시작합니다.")

    def save_state(self):
        data = {
            "quizzes": [quiz.to_dict() for quiz in self.quizzes],
            "best_score": self.best_score
        }

        try:
            with open(self.state_file, "w", encoding="utf-8") as file:
                json.dump(data, file, ensure_ascii=False, indent=4)
        except OSError:
            print("파일 저장 중 오류가 발생했습니다.")

    def safe_input(self, prompt):
        try:
            return input(prompt)
        except KeyboardInterrupt:
            print("\n입력이 중단되었습니다. 현재 상태를 저장하고 종료합니다.")
            self.save_state()
            self.is_running = False
            return None
        except EOFError:
            print("\n입력이 종료되었습니다. 현재 상태를 저장하고 종료합니다.")
            self.save_state()
            self.is_running = False
            return None

    def show_menu(self):
        print("\n" + "=" * 40)
        print("        나만의 퀴즈 게임")
        print("=" * 40)
        print("1. 퀴즈 풀기")
        print("2. 퀴즈 추가")
        print("3. 퀴즈 목록")
        print("4. 점수 확인")
        print("5. 종료")
        print("=" * 40)

    def get_number_input(self, prompt, min_value, max_value):
        while self.is_running:
            user_input = self.safe_input(prompt)

            if user_input is None:
                return None

            user_input = user_input.strip()

            if user_input == "":
                print(f"입력이 비어 있습니다. {min_value}-{max_value} 사이의 숫자를 입력하세요.")
                continue

            try:
                number = int(user_input)
            except ValueError:
                print(f"잘못된 입력입니다. {min_value}-{max_value} 사이의 숫자를 입력하세요.")
                continue

            if number < min_value or number > max_value:
                print(f"잘못된 입력입니다. {min_value}-{max_value} 사이의 숫자를 입력하세요.")
                continue

            return number

        return None

    def get_non_empty_input(self, prompt):
        while self.is_running:
            user_input = self.safe_input(prompt)

            if user_input is None:
                return None

            user_input = user_input.strip()

            if user_input == "":
                print("빈 입력은 허용되지 않습니다. 다시 입력하세요.")
                continue

            return user_input

        return None

    def play_quiz(self):
        if len(self.quizzes) == 0:
            print("등록된 퀴즈가 없습니다.")
            return

        print(f"\n퀴즈를 시작합니다. 총 {len(self.quizzes)}문제입니다.")
        correct_count = 0

        for index, quiz in enumerate(self.quizzes, start=1):
            if not self.is_running:
                return

            print("\n" + "-" * 40)
            print(f"[문제 {index}]")
            quiz.display()

            user_answer = self.get_number_input("정답 입력(1-4): ", 1, 4)
            if user_answer is None:
                return

            if quiz.is_correct(user_answer):
                print("정답입니다.")
                correct_count += 1
            else:
                correct_choice = quiz.choices[quiz.answer - 1]
                print(f"오답입니다. 정답은 {quiz.answer}번 ({correct_choice})입니다.")

        score = int((correct_count / len(self.quizzes)) * 100)

        is_new_best = False
        if self.best_score is None or correct_count > self.best_score:
            self.best_score = correct_count
            is_new_best = True
            self.save_state()

        print("\n" + "=" * 40)
        print(f"결과: {len(self.quizzes)}문제 중 {correct_count}문제 정답")
        print(f"점수: {score}점")

        if is_new_best:
            print("새로운 최고 점수입니다.")
        else:
            best_percent = int((self.best_score / len(self.quizzes)) * 100)
            print(f"현재 최고 점수: {self.best_score}문제 정답 ({best_percent}점)")

        print("=" * 40)

    def add_quiz(self):
        print("\n새 퀴즈를 추가합니다.")

        question = self.get_non_empty_input("문제를 입력하세요: ")
        if question is None:
            return

        choices = []
        for index in range(1, 5):
            choice = self.get_non_empty_input(f"선택지 {index}: ")
            if choice is None:
                return
            choices.append(choice)

        answer = self.get_number_input("정답 번호를 입력하세요 (1-4): ", 1, 4)
        if answer is None:
            return

        new_quiz = Quiz(question, choices, answer)
        self.quizzes.append(new_quiz)
        self.save_state()

        print("퀴즈가 추가되었습니다.")

    def list_quizzes(self):
        if len(self.quizzes) == 0:
            print("등록된 퀴즈가 없습니다.")
            return

        print(f"\n등록된 퀴즈 목록 (총 {len(self.quizzes)}개)")
        print("-" * 40)

        for index, quiz in enumerate(self.quizzes, start=1):
            print(f"[{index}] {quiz.question}")

        print("-" * 40)

    def show_best_score(self):
        if self.best_score is None:
            print("아직 퀴즈를 풀지 않았습니다.")
            return

        total_quiz_count = len(self.quizzes)

        if total_quiz_count == 0:
            print(f"최고 점수: {self.best_score}문제 정답")
            return

        best_percent = int((self.best_score / total_quiz_count) * 100)
        print(f"최고 점수: {self.best_score}문제 정답 ({best_percent}점)")

    def run(self):
        try:
            while self.is_running:
                self.show_menu()
                choice = self.get_number_input("선택: ", 1, 5)

                if choice is None:
                    break

                if choice == 1:
                    self.play_quiz()
                elif choice == 2:
                    self.add_quiz()
                elif choice == 3:
                    self.list_quizzes()
                elif choice == 4:
                    self.show_best_score()
                elif choice == 5:
                    print("프로그램을 종료합니다.")
                    self.save_state()
                    break
        finally:
            self.save_state()


if __name__ == "__main__":
    game = QuizGame()
    game.run()