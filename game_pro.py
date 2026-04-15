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
    

class QuizGame:
    def __init__(self):
        self.quizzes = [
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

    def show_menu(self):

        print("나만의 퀴즈 게임")
        print("=" * 40)
        print("1. 퀴즈 풀기")
        print("2. 퀴즈 추가")
        print("3. 퀴즈 목록")
        print("4. 점수 확인")
        print("5. 종료")

    def get_number_input(self, prompt, min_value, max_value):
        while True:
            user_input = input(prompt).strip()

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
        
    def play_quiz(self):
        if len(self.quizzes) == 0:
            print("등록된 퀴즈가 없습니다.")
            return

        print(f"\n퀴즈를 시작합니다. 총 {len(self.quizzes)}문제입니다.")
        correct_count = 0

        for index, quiz in enumerate(self.quizzes, start=1):
            print("\n" + "-" * 40)
            print(f"[문제 {index}]")
            quiz.display()

            user_answer = self.get_number_input("정답 입력(1-4): ", 1, 4)

            if quiz.is_correct(user_answer):
                print("정답입니다.")
                correct_count += 1
            else:
                correct_choice = quiz.choices[quiz.answer - 1]
                print(f"오답입니다. 정답은 {quiz.answer}번 ({correct_choice})입니다.")

        score = int((correct_count / len(self.quizzes)) * 100)

        print("\n" + "=" * 40)
        print(f"결과: {len(self.quizzes)}문제 중 {correct_count}문제 정답")
        print(f"점수: {score}점")
        print("=" * 40)


    def run(self):
        while True:
            self.show_menu()
            choice = self.get_number_input("선택: ", 1, 5)

            if choice == 1:
                self.play_quiz()
            elif choice == 2:
                print("퀴즈 추가")
            elif choice == 3:
                print("퀴즈 목록")
            elif choice == 4:
                print("점수 확인")
            elif choice == 5:
                print("프로그램을 종료합니다.")
                break


if __name__ == "__main__":
    game = QuizGame()
    game.run()