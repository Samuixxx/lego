import enum
import asyncio
import json
import websockets
from utils.motor.motorenums.direction import Direction
from utils.motor.motorenums.turn import Turn
from utils.motor.motorenums.speed_controls import SpeedControls
from utils.motor.motorenums.turn_controls import TurnControls


class MotorUtils:
    """
    Classe per la gestione del motore LEGO tramite WebSocket.

    Attributi:
        websocket (WebSocket): Connessione WebSocket per inviare aggiornamenti.
        motor (oggetto): Rappresenta il motore fisico (da definire con PiStorms o altra libreria).
        speed (int): Velocità attuale del motore.
        direction (Direction): Direzione attuale del motore (fermo, avanti, indietro, ecc.).
        is_moving (bool): Indica se il motore è in movimento.
        UPDATE_VELOCITY_TIMELAPS (float): Intervallo di aggiornamento della velocità in secondi.
    """

    def __init__(self, websocket):
        """
        Inizializza la classe MotorUtils con il WebSocket e le variabili di stato.

        Args:
            websocket (WebSocket): Connessione WebSocket per la comunicazione con il client.
        """
        self.websocket = websocket  # Connessione WebSocket per il controllo remoto
        self.motor = None  # Placeholder per il motore fisico (da definire con PiStorms o altra libreria)
        self._move_speed = 0  # Velocità iniziale
        self._turn_angle = 0 # Angolo iniziale di rotazione
        self._is_moving = False  # Stato del movimento
        self._is_turning = False  # Stato della rotazione
        self._UPDATE_VELOCITY_TIME_OFFSET = 0.3  # Intervallo di aggiornamento della velocità in secondi
        self.__is_motor_started = False # Variabile booleana che controlla che il client abbia acceso il motore prima di poter muovere il lego    

    def _toggle_motor_status(self) -> None:
        """ 
        Inverte lo stato del motore in risposta a una richiesta del client.  
        
        Se il motore è attivo, viene spento. Se è spento, viene attivato.  
        """
        self.__is_motor_started = not self.__is_motor_started

    async def _turn(self, side: Turn, additional_delay: float = 0.2) -> None:
        """ 
        Regola progressivamente l'angolo di sterzata per girare a sinistra o a destra.  
        
        Parametri:  
        - `side` (Turn): Direzione della sterzata (sinistra o destra).  
        - `additional_delay` (float, default 0.2): Ritardo aggiuntivo prima di fermare la sterzata.  
        
        Funzionamento:  
        - Se è già in corso una sterzata, la funzione esce immediatamente per evitare esecuzioni multiple.  
        - Modifica l'angolo di sterzata incrementandolo/decrementandolo progressivamente fino al massimo consentito.  
        - Interrompe l'incremento se il tasto viene rilasciato (`_stop_turning` diventa `True`).  
        - Invia l'angolo aggiornato al client tramite WebSocket.  
        - Si assicura di non inviare dati ridondanti se l'angolo non cambia.  
        """

        if self._is_turning or self.__is_motor_started:
            return  # Evita esecuzioni multiple
        
        self._is_turning = True # imposto il flag che indica che sto sterzando
        self._stop_turning = False # variabile per evitare che se rilascio il tasto prima del completamento del ciclo while continui ad incrementare i gradi
        turn_increment = -1 if side == Turn.LEFT else 1 # calcolo l'incremento in base alla direzione del motore prima del controsterzo
        max_angle = TurnControls.MAXIMUM_TURN_ANGLE.value # richiamo al valore massimo di angolatura dall'enum TurnControls

        while self._turn_angle < max_angle and not self._stop_turning: # continuo il ciclo finche l'angolo non supera il limite massimo (max_angle) e non viene impostato a true il flag di _stop_turning in self._turn
            new_angle = self._turn_angle + turn_increment # aggiungo l'incremento a self._turn_angle salvandolo in una nuova variabile
            new_angle = max(-max_angle, min(new_angle, max_angle)) # calcolo il valore dell'angolo limitandolo tra -60 gradi e il minimo tra new_angle e max_angle -> sempre new_angle
            
            if new_angle == self._turn_angle: # controllo che new_angle non sia uguale a 
                break  # Evita di inviare dati ripetuti
            
            self._turn_angle = new_angle # imposto _turn_angle come new_angle per aggiornare la condizione del while
            await self.websocket.send(json.dumps({"ok": True, "angle": self._turn_angle})) # mando i dati al client
            await asyncio.sleep(0.01)
        
        self._is_turning = False


    async def _unturn(self) -> None:
        """
        Gradualmente riporta l'angolo di rotazione (`self._turn_angle`) a 0.

        Se l'angolo è già 0, la funzione termina immediatamente. Altrimenti,
        decrementa o incrementa l'angolo di 1 unità alla volta, a seconda del
        segno dell'angolo corrente. Dopo ogni modifica, invia l'angolo aggiornato
        al client tramite il websocket.

        La funzione utilizza `asyncio.sleep(0.1)` per introdurre una pausa tra
        ogni aggiornamento dell'angolo, permettendo una transizione graduale.

        Una volta che l'angolo raggiunge 0, invia un messaggio finale al client
        con l'angolo impostato a 0.

        Stampa messaggi di debug per indicare quando l'angolo è già 0 e quando
        è stato riportato a 0.

        Args:
            self: L'istanza della classe che contiene l'angolo di rotazione e il websocket.

        Returns:
            None
        """
        if not self.__is_motor_started:
            return  # Evita esecuzioni se il motore non è acceso
        
        if self._turn_angle == 0:
            print("L'angolo è già a 0.")
            return  # Esci immediatamente se già a zero
        
        self._stop_turning = True

        turn_increment = 1 if self._turn_angle > 0 else -1

        while self._turn_angle != 0 and not self._is_turning:
            # Decremento o incremento progressivamente l'angolo
            self._turn_angle -= turn_increment

            # Invia l'angolo aggiornato al client
            await self.websocket.send(json.dumps({"ok": True, "angle": self._turn_angle}))
            await asyncio.sleep(0.1)

        print("Angolo riportato a 0.")
    
    async def _move_forward(self) -> None:
        """
        Avvia il movimento del motore in avanti, incrementando la velocità gradualmente.

        Se il motore è già in movimento, la velocità viene incrementata di 1, con un limite massimo impostato dal valore di `SpeedControls.MAXIMUM_PER_GEAR`.
        La funzione simula una pausa per consentire un incremento graduale della velocità. Se la velocità supera il limite, viene limitata al valore massimo consentito.

        :return: La velocità corrente del motore dopo l'incremento.
        """
        if self._is_moving:
            # Incrementa la velocità, ma non oltre il massimo consentito
            self._move_speed += 1
            if self._move_speed > SpeedControls.MAXIMUM_PER_GEAR.value:
                self._move_speed = SpeedControls.MAXIMUM_PER_GEAR.value

            await self.websocket.send(json.dumps({
                "ok": True, "motorspeed": self._move_speed
            }))

            # Attende un intervallo per simulare un incremento graduale
            await asyncio.sleep(self._UPDATE_VELOCITY_TIME_OFFSET)

    async def _move_backward(self) -> None:
        """
        Riduce gradualmente la velocità per muovere il motore all'indietro.
        
        - La velocità diminuisce di 1 a ogni iterazione.
        - Se la velocità supera il limite negativo massimo, viene bloccata a quel valore.
        - Introduce una pausa per simulare un rallentamento progressivo.
        
        Returns:
            int: Velocità attuale dopo l'aggiornamento.
        """
        additional_delay = 0.4  # Ritardo aggiuntivo per una transizione più fluida

        if self._is_moving:
            # Riduce la velocità per muovere il motore all'indietro
            self._move_speed -= 1  

            # Impedisce che la velocità superi il limite massimo negativo
            max_backward_speed = -SpeedControls.MAXIMUM_VALOCITY_BACKWARD.value
            if self._move_speed < max_backward_speed:
                self._move_speed = max_backward_speed

            await self.websocket.send(json.dumps({
                "ok": True, "motorspeed": self._move_speed
            }))

            # Pausa per simulare la riduzione graduale della velocità
            await asyncio.sleep(self._UPDATE_VELOCITY_TIME_OFFSET + additional_delay)

    async def _stop(self) -> None:
        """
        Ferma il movimento del motore riducendo gradualmente la velocità.

        Se il motore è in movimento, la velocità viene ridotta gradualmente fino a zero. 
        La velocità viene inviata al client ogni volta che cambia, per mantenere aggiornato 
        lo stato sul lato client. Al termine del ciclo di decelerazione, la velocità viene 
        impostata su zero e il motore viene fermato.

        :return: La velocità finale del motore (zero).
        """
        additional_delay = 0
        if self._move_speed != 0:
            while self._move_speed != 0:
                # Riduci la velocità gradualmente
                if self._move_speed > 0:
                    self._move_speed -= 1  # Decellero per tornare a 0 km/h
                    if self._move_speed > 10:
                        additional_delay = 0.1
                    elif self._move_speed > 5:
                        additional_delay = 0.3
                    else:
                        additional_delay = 0.5
                elif self._move_speed < 0:
                    self._move_speed += 1  # Decellero per tornare a 0 km/h
                    if self._move_speed > -10:
                        additional_delay = 0.5  # Ritardo per velocità basse in retromarcia
                    elif -20 <= self._move_speed <= -10:
                        additional_delay = 0.3  # Ritardo per velocità medie in retromarcia
                    elif -35 >= self._move_speed >= -20:
                        additional_delay = 0.1

                # Invia la velocità aggiornata solo quando cambia
                await self.websocket.send(json.dumps({
                    "ok": True, "motorspeed": self._move_speed
                }))

                await asyncio.sleep(self._UPDATE_VELOCITY_TIME_OFFSET + additional_delay)

        if self._move_speed == 0:
            await self.websocket.send(json.dumps({
                "ok": True, "motorspeed": 0
            }))

    async def _execute_move(self, direction: Direction, turn: Turn = Turn.STRAIGHT) -> None:
        """
        Avvia il movimento e la sterzata in parallelo utilizzando asyncio.gather.
        """

        if not self.__is_motor_started:
            return

        if direction not in {Direction.FORWARD, Direction.BACKWARD, Direction.STOP}:
            raise ValueError("Direzione non valida. Usa Direction.FORWARD, Direction.BACKWARD o Direction.STOP.")

        if turn not in {Turn.LEFT, Turn.RIGHT, Turn.STRAIGHT}:
            raise ValueError("Turn non valido. Usa Turn.LEFT, Turn.RIGHT o Turn.STRAIGHT.")

        self._is_moving = direction != Direction.STOP
        self._is_turning = turn != Turn.STRAIGHT

        tasks = []

        # Avvia il movimento
        match direction:
            case Direction.FORWARD:
                tasks.append(self._move_forward())
            case Direction.BACKWARD:
                tasks.append(self._move_backward())
            case Direction.STOP:
                tasks.append(self._stop())

        # Avvia la sterzata
        if self._is_turning:
            tasks.append(self._turn(turn))
        elif self._turn_angle != 0:
            tasks.append(self._unturn())

        # Esegui le task in parallelo solo se ci sono task
        await asyncio.gather(*tasks)

    


