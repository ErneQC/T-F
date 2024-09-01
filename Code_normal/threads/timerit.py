import time
import logging

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