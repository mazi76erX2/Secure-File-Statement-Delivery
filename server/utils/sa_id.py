"""Utilities for South African ID number handling."""


def validate_sa_id(id_number: str) -> bool:
    if not id_number.isdigit() or len(id_number) != 13:
        return False

    month = int(id_number[2:4])
    day = int(id_number[4:6])
    if month < 1 or month > 12:
        return False
    if day < 1 or day > 31:
        return False

    digits = [int(char) for char in id_number]
    check_digit = digits[-1]

    odd_sum = sum(digits[0:12:2])

    even_digits = "".join(str(d) for d in digits[1:12:2])
    doubled = str(int(even_digits) * 2).zfill(len(even_digits) + 1)
    even_sum = sum(int(char) for char in doubled)

    total = odd_sum + even_sum
    calc_check = (10 - (total % 10)) % 10
    return calc_check == check_digit
