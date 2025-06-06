import string
import secrets
import bcrypt


def generate_password(length=12):
    # Define the characters to be used in the password
    characters = string.ascii_letters + string.digits + string.punctuation

    # Generate a secure random password using secrets module
    return ''.join(secrets.choice(characters) for _ in range(length))


def hash_password(password):
    # Generate a salt
    salt = bcrypt.gensalt()

    # Hash the password using the salt
    return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')


def check_password(password, hashed_password):
    # Verify the password against the hashed password
    return bcrypt.checkpw(password.encode('utf-8'), hashed_password.encode('utf-8'))


if __name__ == '__main__':
    # Generate a secure password with default length of 12
    # secure_password = generate_password()
    secure_password = 'mypassword'
    print(f"Secure password: {secure_password}")

    # Hash the password
    hashed_password = hash_password(secure_password)
    print(f"Hashed password: {hashed_password}")

    hashed_password_2 = hash_password(secure_password)
    print(f"Hashed password: {hashed_password_2}")

    print()

    # Check if a given password matches the stored hashed password
    wrong_password = "wrongpassword"
    is_password_matched = check_password(wrong_password, hashed_password)
    print(f"check password ({wrong_password}) --- Is password matched: {is_password_matched}")

    is_password_matched = check_password(secure_password, hashed_password)
    print(f"check password ({secure_password}) --- Is password matched: {is_password_matched}")

    is_password_matched_2 = check_password(secure_password, hashed_password_2)
    print(f"check password ({secure_password}) --- Is password matched: {is_password_matched_2}")

