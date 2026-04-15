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

    def run(self):
        while True:
            self.show_menu()
            choice = self.get_number_input("선택: ", 1, 5)

            if choice == 1:
                print("퀴즈 풀기")
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