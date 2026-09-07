# These are helper tools that are gonna help us to do certain things in our app

# Create User
def create_user(user_list, user_id, user_name, user_phoneNo, user_address, user_package):
    user = {
        "user_id": user_id,
        "user_name" : user_name,
        "user_phoneNo": user_phoneNo,
        "user_address": user_address,
    }
