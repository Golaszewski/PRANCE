#include <avr/io.h>
#include "usi_i2c_slave.h"

#define DRIVER_IN1_PIN 3 //PB3, chip pin 2
#define DRIVER_IN1_MASK (1 << DRIVER_IN1_PIN)

//Define a reference to the I2C slave register bank pointer array
extern char* USI_Slave_register_buffer[];

int main()
{
    //Create 16-bit PWM value
    unsigned int pwm_val = 9;

    //Assign the pwm value low byte to I2C internal address 0x00
    //Assign the pwm value high byte to I2C internal address 0x01
    USI_Slave_register_buffer[0] = (unsigned char*)&pwm_val;
    USI_Slave_register_buffer[1] = (unsigned char*)(&pwm_val)+1;

    //Initialize I2C slave with slave device address 0x40
    USI_I2C_Init(0x60);

    //Set up driver pin as output
    DDRB |= DRIVER_IN1_MASK;

    unsigned int i;
    while(1)
    {
        PORTB |= DRIVER_IN1_MASK; //Turn pump on
        for(i = 0; i < pwm_val; i++)
        {
            PORTB &= ~(DRIVER_IN1_MASK); //Turn pump off
        }
    }
}
