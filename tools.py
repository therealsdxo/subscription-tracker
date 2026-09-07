# These are helper tools that are gonna help us to do certain things in our app

# Create User Function
users = {}

def create_user(users, user_id, user_name, user_phoneNo, user_address, user_package):
    if user_id in users:
        raise ValueError(f"User ID {user_id} already exists")
    users[user_id] = {
        "user_name": user_name,
        "user_phoneNo": user_phoneNo,
        "user_address": user_address,
        "user_package": user_package
    }
    return users[user_id]

# Update Created User
def update_user(users, user_id, **kwargs):
    if user_id not in users:
        raise ValueError(f"User ID {user_id} does not exist")
    
    users[user_id].update(kwargs)
    return users[user_id]


# Delete A particular user
def delete_user(users, user_id):
    if user_id not in users:
        raise ValueError(f"User ID {user_id} does not exist")
    
    deleted_user = users.pop(user_id)
    return deleted_user

# Get User through User Id
def get_user(users, user_id):
    if user_id not in users:
        raise ValueError(f"User ID {user_id} does not exist")
    return users[user_id]

# Create package function
packages = {}

def create_package(packages, package_id, package_name, package_price, package_duration):
    if package_id in packages:
        raise ValueError(f"Package ID {package_id} already exists")
    packages[package_id] = {
        "package_name": package_name,
        "package_price": package_price,
        "package_duration": package_duration
    }
    return packages[package_id]