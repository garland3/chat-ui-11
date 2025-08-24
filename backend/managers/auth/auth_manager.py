
# this is the ONLy authorization check that can be used. 
# NOTE to users, you should override this with your company logic if you choose to use this project
# NO fallbacks. This function must be called. Do not allow any edge cases or any access to unknown users
# Do not trust the user, always use server provided identity instead of any claims by the user. 
def is_user_in_group(username, group):
    # TODO implement this.
    groups_for_test_user = ["test_group", "admin_group", "engineering"]
    return group in groups_for_test_user


# more AuthorizationManager code here. 