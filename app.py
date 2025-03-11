from p2p import p2p_argument, call_number  # Import the functions from helpers.py

def main():
    # Receive doctor's arguments
    argument = p2p_argument()
    print(argument)
    
    number = input("Please input the phone number of who you wish for me to call: ")

    # Call number and return transcript
    call_number(number, argument)

if __name__ == "__main__":
    main()