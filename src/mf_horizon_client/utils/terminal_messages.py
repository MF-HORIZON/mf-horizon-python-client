def print_success(message: str):
    print(f"\n \u2714 {message}")


def print_failure(message: str):
    print(f"\n \u274c {message}")


def print_server_error_details(error_message: str):
    print(f"\nServer Message:\n\n ==> {error_message}\n")


def print_expert_message(message: str):
    print(f"\n \u24D8  EXPERT {message}\n")


def print_update(message: str):
    print(f"\n \u24D8 {message}\n")


def print_warning(message: str):
    print(f"\n \u24D8 WARN: {message}\n")
