
# __version__ = '0.0.1'

# from payments.templates.pages import razorpay_checkout
# from thirvusoft_bpm.thirvusoft_bpm.code_backup.razorpay_checkout import gets_context

# razorpay_checkout.get_context = gets_context

# from thirvusoft_bpm.patches.custom_razorpay_setting import monkey_patch_razorpay

# monkey_patch_razorpay()
# from thirvusoft_bpm.patches.custom_razorpay_setting import monkey_patch_razorpay
# monkey_patch_razorpay()
# #

# __version__ = '0.0.1'

# Override Razorpay Checkout context
# from payments.templates.pages import razorpay_checkout
# from thirvusoft_bpm.thirvusoft_bpm.code_backup.razorpay_checkout import gets_context
# razorpay_checkout.get_context = gets_context

# # # Monkeypatch Razorpay authorize/capture
# from thirvusoft_bpm.patches.custom_razorpay_setting import monkey_patch_razorpay
# monkey_patch_razorpay()

__version__ = "0.0.1"

# ---------------------------------------------
# Safe override of Razorpay Checkout context
# ---------------------------------------------
try:
    from payments.templates.pages import razorpay_checkout
    from thirvusoft_bpm.thirvusoft_bpm.code_backup.razorpay_checkout import gets_context

    if hasattr(razorpay_checkout, "get_context"):
        razorpay_checkout.get_context = gets_context
    else:
        print("Warning: razorpay_checkout.get_context not found")

except Exception as e:
    print(f"Error while overriding Razorpay Checkout context: {e}")


# ---------------------------------------------
# Safe import & execution of monkey-patch logic
# ---------------------------------------------
try:
    from thirvusoft_bpm.patches.custom_razorpay_setting import monkey_patch_razorpay

    if callable(monkey_patch_razorpay):
        monkey_patch_razorpay()
    else:
        print("Warning: monkey_patch_razorpay is not callable")

except Exception as e:
    print(f"Error while monkey-patching Razorpay: {e}")


