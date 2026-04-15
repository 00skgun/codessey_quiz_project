class QuizGame:
    def show_menu(self):
        print("\n" + "=" * 40)
        print("       나만의 퀴즈 게임")
        print("1. 퀴즈 풀기")
        print("2. 퀴즈 추가")
        print("3. 퀴즈 목록")
        print("4. 점수 확인")
        print("5. 종료")

    def run(self):
        while True:
            self.show_menu()
            choice = input("선택: ")

            if choice == "1":
                print("퀴즈 풀기")
            elif choice == "2":
                print("퀴즈 추가")
            elif choice == "3":
                print("퀴즈 목록")
            elif choice == "4":
                print("점수 확인")
            elif choice == "5":
                print("프로그램을 종료합니다.")
                break
            else:
                print("잘못된 입력입니다. 1-5 사이의 숫자를 입력하세요.")


if __name__ == "__main__":
    game = QuizGame()
    game.run()