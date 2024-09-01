import time
import logging
import aspectlib
import inspect
# Configuración de logging
logging.basicConfig(level=logging.INFO)
######################################
#Aspectos usando libreria Aspectlib
######################################
@aspectlib.Aspect
def log_calls(cutpoint, *args, **kwargs):
    class_name = "UnknownClass"
    # Intentar extraer el nombre de la clase desde diferentes perspectivas
    if hasattr(cutpoint, '__self__') and cutpoint.__self__ is not None:
        class_name = cutpoint.__self__.__class__.__name__
    elif inspect.isclass(cutpoint):
        class_name = cutpoint.__name__
    elif hasattr(cutpoint, '__class__'):
        class_name = cutpoint.__class__.__name__
    elif hasattr(cutpoint, '__module__'):
        class_name = cutpoint.__module__.split('.')[0]  # como último recurso, usar el nombre del módulo
    try:
        result = yield aspectlib.Proceed  # Ejecutar la función original
    except Exception as e:
        logging.error(f"Exception in Class: {class_name}, Error: {e}")
        raise
    result_str = result if result is not None else "None"
    logging.info(f" {class_name},  {result_str}")
   
    yield aspectlib.Return(result)

@aspectlib.Aspect
def handle_exceptions(cutpoint_function, *args, **kwargs):
    try:
        result = yield aspectlib.Proceed  # Ejecutar la función original
    except Exception as ex:
        function_name = getattr(cutpoint_function, '__name__', str(cutpoint_function))
        logging.error(f"Exception in {function_name}: {ex}")
        raise
    yield aspectlib.Return(result)  # Devolver el resultado final

######################################
#Aspectos usando Decoradores
######################################
def timeit(cutpoint_function):
    def wrapper(self, *args, **kwargs):
        # Registra el tiempo de inicio
        start_time = time.time()
        
        # Ejecuta la función con los argumentos proporcionados
        result = cutpoint_function(self, *args, **kwargs)
        
        # Registra el tiempo de finalización
        end_time = time.time()
        execution_time = end_time - start_time

        # Obtén el nombre de la clase y de la función
        class_name = self.__class__.__name__ if hasattr(self, '__class__') else 'Global'
        func_name = cutpoint_function.__name__
        
        # Imprime el tiempo transcurrido
        logging.info(f" Clase: {class_name}, Función: {func_name} tardó {execution_time:.6f} segundos")
        
        return result

    return wrapper