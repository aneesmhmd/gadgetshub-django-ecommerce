from django.shortcuts import render,redirect, HttpResponse
from django.http import HttpResponseRedirect
from cart.models import Cart, CartItem
from .models import Payment,Order,OrderItem, ReviewRating
from accounts.models import Address
from store.models import Product, Variation
from django.utils import timezone
from django.contrib.auth.decorators import login_required
from .forms import ReviewForm
from django.contrib import messages
import razorpay
from django.conf import settings
from django.core.mail import send_mail


# Create your views here.


@login_required
def success(request):
    try:
        razorpay_order_id = request.GET.get('razorpay_order_id')
        cart = Cart.objects.get(razorpay_order_id=razorpay_order_id)

        # Payment details storing
        user = request.user
        transaction_id = request.GET.get('razorpay_payment_id')
        cart_total = cart.get_cart_total()
        tax = cart.get_tax()
        grand_total = cart.get_grand_total()
        payment = Payment.objects.create(user=user, transaction_id=transaction_id, cart_total=cart_total, tax=tax, grand_total=grand_total)
        payment.save()

        address_id = request.GET.get('address')
        delivery_address = Address.objects.get(user=user, id=address_id)
        
        # Creating the order in Order table
        order = Order.objects.create(order_id=razorpay_order_id, user=user, delivery_address=delivery_address, payment=payment)

        if cart.coupon:
            order.coupon = cart.coupon
            order.save()

        # Storing ordered products in OrderItem table
        order_items = CartItem.objects.filter(cart=cart)
        for item in order_items:
            item.product.stock -= item.quantity
            item.product.save()

            ordered_item = OrderItem.objects.create(user=user,order=order, product=item.product, item_price=item.get_product_price(), quantity=item.quantity, item_total=item.get_sub_total())
            ordered_item.save()
            
            if item.variant:
                ordered_item.variant = item.variant.variation
                ordered_item.save()

        # Deleting the cart once it is ordered/paid
        cart.is_active = False
        cart.delete()

        return render(request, 'orders/success.html', {'order_id': razorpay_order_id})
    
    except:
        return redirect('orders_list')



@login_required
def orders_list(request):
    orders = Order.objects.filter(user=request.user).order_by('-id')
    return render(request, 'orders/orders_list.html', {'orders' : orders})



@login_required
def order_details(request,order_id):
    try:
        order = Order.objects.get(uid=order_id)
        order_items = OrderItem.objects.filter(order=order)
        print(order_items)
    except:
        order_items = None
        
    return render(request, 'orders/order_details.html', {'order_items' : order_items})



@login_required
def order_tracking(request, item_id):
    current_date = timezone.now()
    item = OrderItem.objects.get(id=item_id)

    context = {
        'item' : item,
        'current_date' : current_date
    }
    return render(request, 'orders/order_tracking.html' ,context)



@login_required
def order_invoice(request, order_id):

    order = Order.objects.get(uid=order_id,user=request.user)
    order_items = OrderItem.objects.filter(order=order)

    context = {
        'order' : order,
        'order_items' : order_items
    }
    return render(request, 'orders/invoice.html',context)



@login_required
def submit_review(request, product_id):
    if request.method == 'POST':
        try:
            review = ReviewRating.objects.get(user__id=request.user.id, product__id=product_id)
            form = ReviewForm(request.POST, instance=review)  # Checks whether the review of the product by the user exists.
                                                              # If exists, it will detect that review needs to be updated.
                                                              # Else save it as a new review
                                                              # If instance not passed, it will save it as a new review
            form.save()
            messages.success(request, 'Thank you! Your review has been updated')
            return HttpResponseRedirect(request.META.get('HTTP_REFERER'))
        
        except ReviewRating.DoesNotExist:
            form = ReviewForm(request.POST)
            
            if form.is_valid():
                data = ReviewRating()
                data.review = form.cleaned_data['review']
                data.rating = form.cleaned_data['rating']
                data.user = request.user
                data.product_id = product_id
                data.save()
                messages.success(request, 'Thank you! Your review have been saved.')
                return HttpResponseRedirect(request.META.get('HTTP_REFERER'))
            
    messages.error(request, 'Not success')
    return HttpResponseRedirect(request.META.get('HTTP_REFERER'))



@login_required
def cancel_order(request, item_id=None, order_id=None):
        
        client = razorpay.Client(auth=(settings.RAZOR_KEY_ID, settings.RAZOR_KEY_SECRET))
        order = Order.objects.get(order_id=order_id,user=request.user)
        payment_id = order.payment.transaction_id
        item = OrderItem.objects.get(order=order, id=item_id)
        item_amount = int(item.item_total) * 100
        
        refund = client.payment.refund(payment_id,{'amount':item_amount})

        if refund is not None:
            item.order_status = 'Refunded'
            item.product.stock += item.quantity
            item.product.save()

            current_user = request.user
            subject = "Refund succesfull!"
            mess = f'Greetings {current_user.first_name}.\nYour refund for the product {item} of order: {order.order_id} has been succesfully generated. \nThank you for shopping with us!'
            send_mail(
                        subject,
                        mess,
                        settings.EMAIL_HOST_USER,
                        [current_user.email],
                        fail_silently = False
                     )

            item.save()
            return render(request, 'orders/refund_success.html',{'order_id':order_id})

        else:
            return HttpResponse('Payment not captured')
    
       



    
        
# def cancelOrder(request,id):

#    client = razorpay.Client(auth=(homely.settings.API_KEY, homely.settings.RAZORPAY_SECRET_KEY))
#    # client = razorpay.Client(auth=("rzp_test_d8CuRUKczNyzCd", "8rt6NVn4AxDo7FCkDPmq9k8l"))
#    order = Order.objects.get(id=id,user=request.user)
#    payment=order.payment
#    msg=''
#    if (payment.payment_method == 'Paid by Razorpay'):
#       payment_id = payment.payment_id
#       amount = payment.amount_paid
#       amount=amount*100
#       try:
#          captured_amount = client.payment.capture(payment_id,amount)
#          if captured_amount['status'] == 'captured' :
#             refund_data = {
#                "payment_id": payment_id,
#                "amount": amount,  # amount to be refunded in paise
#                "currency": "INR",
#             }
#          else:
#             msg = "Your bank has not completed the payment yet."
#       except:
#          refund_data = {
#             "payment_id": payment_id,
#             "amount": amount,  # amount to be refunded in paise
#             "currency": "INR",
#          }
#       # payment = client.payment.fetch(payment_id)
#       print(payment_id)
#       refund = client.payment.refund(payment_id, refund_data)
#       print(refund)
#       if refund is not None:
#          current_user=request.user
#          order.refund_completed = True
#          order.status = 'Cancelled'
#          payment = order.payment
#          payment.refund_id = refund['id']
#          payment.save()
#          order.save()
#          msg ="Your order has been successfully cancelled and amount has been refunded!"
#          mess=f'Hello\t{current_user.first_name},\nYour order has been canceled,Money will be refunded with in 1 hour\nThanks!'
#          send_mail(
#                         "Hoely Furnitures - Order Cancelled",
#                         mess,
#                         settings.EMAIL_HOST_USER,
#                         [current_user.email],
#                         fail_silently = False
#                      )
#       else :
#          msg ="Your order is not cancelled because the refund couldnot be  completed now. Please try again later. If the issue continues, CONTACT THE SUPPORT TEAM!"
#          pass
#    else :
#       if(payment.paid):
#          order.refund_completed = True
#          order.status = 'Cancelled'
#          msg ="YOUR ORDER HAS BEEN SUCCESSFULLY CANCELLED!"
#          order.save()
#       else:
#          order.status = 'Cancelled'
#          order.save()
#          msg ="Your payment has not been recieved yet. But the order has been cancelled.!"
#    orderitems = OrderProduct.objects.filter(order=order)
#    context={
#         'order': order,
#         'orderitems':orderitems,
#         'msg':msg
#     }
#    return render(request,'order/vieworder.html',context)