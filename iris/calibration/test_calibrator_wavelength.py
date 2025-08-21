"""
This class handles the calibration to map spectrometer pixels to wavelengths using 
reference peaks
"""
from scipy.optimize import curve_fit
import matplotlib.pyplot as plt
import numpy as np
import matplotlib
matplotlib.use('Agg')

def test():
    read = """sample	reference
            251	620.9
            334	795.8
            436	1001.4
            451	1031.8
            515	1155.3
            674	1450.5
            762	1602.3
            """
    measured_wavelengths = []
    reference_wavelengths = []
    
    for line in read.split('\n'):
        if line.strip() == '':
            continue
        if 'sample' in line:
            continue
        line = line.split('\t')
        measured_wavelengths.append(float(line[0]))
        reference_wavelengths.append(float(line[1]))
        
    print(measured_wavelengths)
    print(reference_wavelengths)
            
    # measured_wavelengths = [158, 716, 680, 436, 762]
    # reference_wavelengths = [546, 576, 579, 564.17, 583.97]
    
    def _calculate_transfer_func_cubic(list_peakRS_mea:list[float],list_peakRS_ref:list[float]) -> tuple[float,float,float,float]:
        """
        Generates the transfer function from the peaks found and the reference peaks
        
        Args:
            list_peakRS_mea (list[float]): List of the Raman shift peaks of the sample representative
            list_peakRS_ref (list[float]): List of the Raman shift peaks of the reference
        
        Returns:
            tuple[float,float,float,float]: The coefficients of the transfer function (a,b,c,d) for the cubic function of a*x**3 + b*x**2 + c*x + d
        """
        def cubic(x,a,b,c,d):
            return a*x**3 + b*x**2 + c*x + d
        
        # Fit the transfer function
        popt,_ = curve_fit(cubic,xdata=list_peakRS_mea,ydata=list_peakRS_ref)
        return popt
    
    def plot_transfer_func(transfer_func_coeff:list,list_peakRS_mea:list[float],list_peakRS_ref:list[float]):
        """
        Plots the transfer function
        
        Args:
            transfer_func_coeff (list): The coefficients of the transfer function
            list_peakRS_mea (list[float]): List of the Raman shift peaks of the sample representative
            list_peakRS_ref (list[float]): List of the Raman shift peaks of the reference
        """
        # Generate the x and y values from the transfer function
        x_min = min(list_peakRS_mea)
        x_max = max(list_peakRS_mea)
        x = np.linspace(x_min,x_max,100)
        y = np.polyval(transfer_func_coeff,x)

        # Generate the plot
        fig,ax = plt.subplots(1,1,figsize=(8,6))
        ax.cla()
        ax.plot(x,y,c='b',label='Transfer function')
        ax.scatter(list_peakRS_mea,list_peakRS_ref,c='r',label='Peaks')
        ax.set_xlabel('Measurement Raman shift peaks[cm-1]')
        ax.set_ylabel('Reference Raman shift peaks[cm-1]')
        ax.set_title('Wavenumber calibration transfer function')
        ax.legend()

        # Add a label to each scatter points
        for i,txt in enumerate(list_peakRS_mea):
            ax.annotate(txt,(list_peakRS_mea[i],list_peakRS_ref[i]))
        
        # Show the plot
        plt.show()
    
    result = _calculate_transfer_func_cubic(measured_wavelengths,reference_wavelengths)
    print(result)
    
    plot_transfer_func(result,measured_wavelengths,reference_wavelengths)
    
def test_save_json():
    import json
    import os
    
    data = {
        'sample': [158, 716, 680, 436, 762],
        'reference': [546, 576, 579, 564.17, 583.97],
        'a': 1.0,
        'b': 2.0,
        'c': 3.0,
        'd': 4.0
    }
    
    savepath = 'test.json'
    with open(savepath,'w') as f:
        json.dump(data,f)
        
    with open(savepath,'r') as f:
        loaded_data = json.load(f)
        
    os.remove(savepath)
    print(loaded_data)
    
    print(type(loaded_data['sample']))
    print(type(loaded_data['sample'][0]))
    
    
if __name__ == '__main__':
    test()
    test_save_json()