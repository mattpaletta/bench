import concurrent.futures


# def copy_future_state(source, destination):
#     if source.cancelled():
#         destination.cancel()
#     if not destination.set_running_or_notify_cancel():
#         return
#     exception = source.exception()
#     if exception is not None:
#         destination.set_exception(exception)
#     else:
#         result = source.result()
#         destination.set_result(result)


# def chain(pool, future, fn):
#     result = concurrent.futures.Future()
#
#     def callback(_):
#         try:
#             temp = pool.submit(fn, future.result())
#             copy = lambda _: copy_future_state(temp, result)
#             temp.add_done_callback(copy)
#         except:
#             result.cancel()
#             raise
#
#     future.add_done_callback(callback)
#     return result
